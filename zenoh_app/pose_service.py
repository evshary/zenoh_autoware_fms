import zenoh
import time
from dataclasses import dataclass
from pycdr2 import IdlStruct
from pycdr2.types import float32, float64, sequence, array
from zenoh_ros_type.rcl_interfaces import Time
from zenoh_ros_type.common_interfaces.std_msgs import Header
from zenoh_ros_type.common_interfaces import Point, Twist, Vector3
from zenoh_ros_type.autoware_auto_msgs import EngageRequest
from zenoh_ros_type.service import ServiceHeader

from lanelet2.projection import UtmProjector
from lanelet2.io import Origin
from lanelet2.core import BasicPoint3d, GPSPoint

import struct
from .map_parser import OrientationParser

@dataclass
class GeoPoint(IdlStruct, typename="GeoPoint"):
    latitude: float64
    longitude: float64
    altitude: float64

@dataclass
class GeoPointStamped(IdlStruct, typename="GeoPointStamped"):
    header: Header
    position: GeoPoint

@dataclass
class Quaternion(IdlStruct, typename="Quaternion"):
    x: float64
    y: float64
    z: float64
    w: float64

@dataclass
class Pose(IdlStruct, typename="Pose"):
    position: Point
    orientation: Quaternion

@dataclass
class PoseWithCovariance(IdlStruct, typename="PoseWithCovariance"):
    pose: Pose
    covariance: array[float64, 36]

@dataclass
class PoseStamped(IdlStruct, typename="PoseStamped"):
    header: Header
    pose: Pose

@dataclass
class PoseWithCovarianceStamped(IdlStruct, typename="PoseWithCovarianceStamped"):
    header: Header
    pose: PoseWithCovariance

@dataclass
class TwistWithCovariance(IdlStruct, typename="TwistWithCovariance"):
    twist: Twist
    covariance: array[float64, 36]

@dataclass
class TwistWithCovarianceStamped(IdlStruct, typename="TwistWithCovarianceStamped"):
    header: Header
    twist: TwistWithCovariance

@dataclass
class Accel(IdlStruct, typename="Accel"):
    linear: Vector3
    angular: Vector3

@dataclass
class AccelWithCovariance(IdlStruct, typename="AccelWithCovariance"):
    accel: Accel
    covariance: array[float64, 36]

@dataclass
class AccelWithCovarianceStamped(IdlStruct, typename="AccelWithCovarianceStamped"):
    header: Header
    accel: AccelWithCovariance

@dataclass
class VehicleKinematics(IdlStruct, typename="VehicleKinematics"):
    geographic_pose: GeoPointStamped
    pose: PoseWithCovarianceStamped
    twist: TwistWithCovarianceStamped
    accel: AccelWithCovarianceStamped


GET_POSE_KEY_EXPR = '/api/vehicle/kinematics'
# GET_POSE_KEY_EXPR = '/sensing/gnss/pose'
# GET_POSE_KEY_EXPR = '/localization/pose_estimator/pose'
SET_ENGAGE_KEY_EXPR = '/api/autoware/set/engageRequest'
SET_GOAL_KEY_EXPR = '/planning/mission_planning/goal'


class VehiclePose():
    def __init__(self, session, scope, use_bridge_ros2dds=False):
        ### Information
        self.use_bridge_ros2dds = use_bridge_ros2dds
        self.session = session
        self.scope = scope
        self.initialize()

    def initialize(self):
        self.lat = 0.0
        self.lon = 0.0

        self.positionX = 0.0
        self.positionY = 0.0

        self.topic_prefix = self.scope if self.use_bridge_ros2dds else self.scope + '/rt'
        self.service_prefix = self.scope if self.use_bridge_ros2dds else self.scope + '/rq'

        self.orientationGen = OrientationParser()

        def callback_position(sample):
            print("Got message of kinematics of vehicle")
            # print("size of the message (bytes) ", struct.calcsize(sample.payload))
            # print(sample.payload)
            data = VehicleKinematics.deserialize(sample.payload)
            # print(data)
            self.positionX = data.pose.pose.pose.position.x
            self.positionY = data.pose.pose.pose.position.y
            # data = PoseStamped.deserialize(sample.payload)
            # self.positionX = data.pose.position.x
            # self.positionY = data.pose.position.y
            print(data)
            self.transform()
            print(self.lat, '|', self.lon)

        ### Topics
        ###### Subscribers
        self.subscriber_pose = self.session.declare_subscriber(self.topic_prefix + GET_POSE_KEY_EXPR, callback_position)

        ###### Publishers
        # self.publisher_gate_mode = self.session.declare_publisher(self.topic_prefix + SET_GATE_MODE_KEY_EXPR)
        self.publisher_goal = self.session.declare_publisher(self.topic_prefix + SET_GOAL_KEY_EXPR)

        ### Service
        ###### Publishers
        self.publisher_engage = self.session.declare_publisher(self.service_prefix + SET_ENGAGE_KEY_EXPR)
        
    def transform(self, originX=0.0, originY=0.0):
        projector = UtmProjector(Origin(originX, originY))
        gps = projector.reverse(BasicPoint3d(self.positionX, self.positionY, 0.0))
        self.lat = gps.lat
        self.lon = gps.lon
        return

    def setGoal(self, lat, lon, originX=0.0, originY=0.0):
        projector = UtmProjector(Origin(originX, originY))
        coordinate = projector.forward(GPSPoint(float(lat), float(lon), 0))
        q = self.orientationGen.genQuaternion_seg(coordinate.x, coordinate.y)
        self.publisher_goal.put(
            PoseStamped(
                header=Header(
                    stamp=Time(
                        sec=0, 
                        nanosec=0
                    ), 
                    frame_id='map'
                ),
                pose=Pose(
                    position=Point(
                        x=coordinate.x,
                        y=coordinate.y,
                        z=0
                    ),
                    orientation=Quaternion(
                        x=q[0],
                        y=q[1],
                        z=q[2],
                        w=q[3]
                    )
                )
            ).serialize()
        )

    def engage(self):
        self.publisher_engage.put(
            EngageRequest(
                ServiceHeader(
                    guid=0,
                    seq=0
                ),
                mode=True
            ).serialize()
        )


class PoseServer():
    def __init__(self, session, use_bridge_ros2dds=False):
        self.use_bridge_ros2dds = use_bridge_ros2dds
        self.session = session
        self.vehicles = {}

    def findVehicles(self, time=10):
        for scope, vehicle in self.vehicles.items():
            vehicle.subscriber_pose.undeclare()

        self.vehicles = {}
        for _ in range(time):
            replies = self.session.get('**/rt/api/vehicle/kinematics', zenoh.Queue())
            for reply in replies:
                key_expr = str(reply.ok.key_expr)
                if 'from_dds' in key_expr:
                    end = key_expr.find('/rt/api/vehicle/kinematics')
                    vehicle = key_expr[:end].split('/')[-1]
                    print(f'find vehicle {vehicle}')
                    self.vehicles[vehicle] = None
        self.constructVehicle()

    def constructVehicle(self):
        for scope in self.vehicles.keys():
            self.vehicles[scope] = VehiclePose(self.session, scope)
    
    def returnPose(self):
        poseInfo = []
        for scope, vehicle in self.vehicles.items():
            poseInfo.append(
                {
                    'name': scope,
                    'lat': vehicle.lat,
                    'lon': vehicle.lon
                }
            )
        return poseInfo

    def setGoal(self, scope, lat, lon):
        if scope in self.vehicles.keys():
            self.vehicles[scope].setGoal(lat, lon)

    def engage(self, scope):
        if scope in self.vehicles.keys():
            self.vehicles[scope].engage()
    



if __name__ == "__main__":
    session = zenoh.open()
    mc = PoseServer(session, 'v1')
    import time
    while True:
        time.sleep(1)
    # msg = VehicleKinematics()



# PoseStamped(header=Header(stamp=Time(sec=0,nanosec=0),frame_id=''),
#                 pose=Pose(
#                     position=Point(
#                         x=coordinate.x,
#                         y=coordinate.y,
#                         z=0
#                     ),
#                     orientation=Quaternion(
#                         x=q[0],
#                         y=q[1],
#                         z=q[2],
#                         w=q[3]
#                     )
#                 )
#             )