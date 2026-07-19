import json
import os
import struct

from lanelet2.core import BasicPoint3d, GPSPoint
from lanelet2.io import Origin
from lanelet2.projection import UtmProjector
from zenoh_ros_type.autoware_adapi_msgs import Route, VehicleKinematics

from .map_parser import OrientationParser

# Pose/route are the bridge-forwarded AD-API topics (raw DDS-CDR); goal/engage
# publish per-scope JSON keys the pinned teleop does not consume yet.
POSE_KEY_FMT = '{scope}/api/vehicle/kinematics'
ROUTE_KEY_FMT = '{scope}/api/routing/route'
GOAL_KEY_FMT = 'manual_control/{scope}/goal'
ENGAGE_KEY_FMT = 'manual_control/{scope}/engage'


class VehiclePose:
    """Per-scope map view: reads pose/route off the bridge, writes goal/engage."""

    def __init__(self, session, scope):
        self.session = session
        self.scope = scope
        self.projector = UtmProjector(Origin(float(os.environ['REACT_APP_MAP_ORIGIN_LAT']), float(os.environ['REACT_APP_MAP_ORIGIN_LON'])))
        self.orientationGen = OrientationParser()

        self.lat = 0.0
        self.lon = 0.0
        self.goalLat = 0.0
        self.goalLon = 0.0
        self.goalValid = False

        self.subscriber_pose = self.session.declare_subscriber(POSE_KEY_FMT.format(scope=scope), self._on_pose)
        self.subscriber_goalPose = self.session.declare_subscriber(ROUTE_KEY_FMT.format(scope=scope), self._on_route)
        self.publisher_goal = self.session.declare_publisher(GOAL_KEY_FMT.format(scope=scope))
        self.publisher_engage = self.session.declare_publisher(ENGAGE_KEY_FMT.format(scope=scope))

        # Route is latched: a one-shot get on join pulls the last route, so a
        # goal set before this view existed still shows.
        self._fetch_route()

    def _fetch_route(self):
        for reply in self.session.get(ROUTE_KEY_FMT.format(scope=self.scope), timeout=1.0):
            if reply.ok is not None:
                self._on_route(reply.ok)
                break

    def _on_pose(self, sample):
        try:
            data = VehicleKinematics.deserialize(sample.payload.to_bytes())
        except (ValueError, struct.error) as e:
            print(f'[PoseService] dropping malformed kinematics sample: {e}')
            return
        gps = self.projector.reverse(BasicPoint3d(data.pose.pose.pose.position.x, data.pose.pose.pose.position.y, 0.0))
        self.lat = gps.lat
        self.lon = gps.lon

    def _on_route(self, sample):
        try:
            data = Route.deserialize(sample.payload.to_bytes())
        except (ValueError, struct.error) as e:
            print(f'[PoseService] dropping malformed route sample: {e}')
            return
        if len(data.data) == 1:
            gps = self.projector.reverse(BasicPoint3d(data.data[0].goal.position.x, data.data[0].goal.position.y, 0.0))
            self.goalLat = gps.lat
            self.goalLon = gps.lon
            self.goalValid = True

    def setGoal(self, lat, lon):
        coordinate = self.projector.forward(GPSPoint(float(lat), float(lon), 0))
        q = self.orientationGen.genQuaternion_seg(coordinate.x, coordinate.y)
        self.publisher_goal.put(json.dumps({'x': coordinate.x, 'y': coordinate.y, 'z': 0.0, 'qx': q[0], 'qy': q[1], 'qz': q[2], 'qw': q[3]}))

    def engage(self):
        self.publisher_engage.put('{}')

    def close(self):
        for entity in (self.subscriber_pose, self.subscriber_goalPose, self.publisher_goal, self.publisher_engage):
            try:
                entity.undeclare()
            except Exception as e:
                print(f'[PoseService] undeclare failed for {self.scope}: {e}')


class PoseServer:
    def __init__(self, session, tracker):
        self.session = session
        self.tracker = tracker
        self.vehicles = {}

    def findVehicles(self):
        present = set(self.tracker.list())
        for scope in present:
            if scope not in self.vehicles:
                self.vehicles[scope] = VehiclePose(self.session, scope)
        # drop vehicles the tracker aged out, undeclaring their subs/pubs
        for scope in [s for s in self.vehicles if s not in present]:
            self.vehicles.pop(scope).close()

    def returnPose(self):
        return [{'name': scope, 'lat': v.lat, 'lon': v.lon} for scope, v in self.vehicles.items()]

    def returnGoalPose(self):
        return [{'name': scope, 'lat': v.goalLat, 'lon': v.goalLon} for scope, v in self.vehicles.items() if v.goalValid]

    def setGoal(self, scope, lat, lon):
        if scope in self.vehicles:
            self.vehicles[scope].setGoal(lat, lon)

    def engage(self, scope):
        if scope in self.vehicles:
            self.vehicles[scope].engage()
