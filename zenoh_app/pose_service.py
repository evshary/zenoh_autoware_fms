import zenoh
import time
from zenoh_ros_type.rcl_interfaces import Time
from zenoh_ros_type.common_interfaces.std_msgs import Header
from zenoh_ros_type.common_interfaces import Point, Quaternion, Vector3
from zenoh_ros_type.common_interfaces import Pose, PoseStamped, PoseWithCovariance, PoseWithCovarianceStamped
from zenoh_ros_type.common_interfaces import Twist, TwistWithCovariance, TwistWithCovarianceStamped
from zenoh_ros_type.common_interfaces import Accel, AccelWithCovariance, AccelWithCovarianceStamped
from zenoh_ros_type.autoware_auto_msgs import EngageRequest
from zenoh_ros_type.service import ServiceHeader
from zenoh_ros_type.geographic_info import GeoPoint, GeoPointStamped
from zenoh_ros_type.autoware_adapi_msgs import VehicleKinematics

from lanelet2.projection import UtmProjector
from lanelet2.io import Origin
from lanelet2.core import BasicPoint3d, GPSPoint

import struct
from .map_parser import OrientationParser

import os



GET_POSE_KEY_EXPR = '/api/vehicle/kinematics'
GET_GOAL_POSE_KEY_EXPR = '/planning/mission_planning/echo_back_goal_pose'
SET_ENGAGE_KEY_EXPR = '/api/autoware/set/engageRequest'
SET_GOAL_KEY_EXPR = '/planning/mission_planning/goal'


class VehiclePose():
    def __init__(self, session, scope, use_bridge_ros2dds=False):
        ### Information
        self.use_bridge_ros2dds = use_bridge_ros2dds
        self.session = session
        self.scope = scope
        self.originX=float(os.environ["REACT_APP_MAP_ORIGIN_LAT"])
        self.originY=float(os.environ["REACT_APP_MAP_ORIGIN_LON"])
        self.projector = UtmProjector(
            Origin(
                self.originX, 
                self.originY
            )
        )
        self.initialize()

    def initialize(self):
        self.lat = 0.0
        self.lon = 0.0

        self.positionX = 0.0
        self.positionY = 0.0

        self.topic_prefix = self.scope if self.use_bridge_ros2dds else self.scope + '/rt'
        self.service_prefix = self.scope if self.use_bridge_ros2dds else self.scope + '/rq'

        self.orientationGen = OrientationParser()

        self.goalX = 0.0
        self.goalY = 0.0
        self.goalLat = 0.0
        self.goalLon = 0.0
        self.goalValid = False

        def callback_position(sample):
            print("Got message of kinematics of vehicle")
            # print("size of the message (bytes) ", struct.calcsize(sample.payload))
            # print(sample.payload)
            data = VehicleKinematics.deserialize(sample.payload)
            # print(data)
            self.positionX = data.pose.pose.pose.position.x
            self.positionY = data.pose.pose.pose.position.y
            gps = self.projector.reverse(BasicPoint3d(self.positionX, self.positionY, 0.0))
            self.lat = gps.lat
            self.lon = gps.lon

        def callback_goalPosition(sample):
            print("Got message of kinematics of vehicle")
            # print("size of the message (bytes) ", struct.calcsize(sample.payload))
            # print(sample.payload)
            data = PoseStamped.deserialize(sample.payload)
            # print(data)
            self.goalX = data.pose.position.x
            self.goalY = data.pose.position.y
            gps = self.projector.reverse(BasicPoint3d(self.goalX, self.goalY, 0.0))
            self.goalLat = gps.lat
            self.goalLon = gps.lon
            self.goalValid = True

        ### Topics
        ###### Subscribers
        self.subscriber_pose = self.session.declare_subscriber(self.topic_prefix + GET_POSE_KEY_EXPR, callback_position)
        self.subscriber_goalPose = self.session.declare_subscriber(self.topic_prefix + GET_GOAL_POSE_KEY_EXPR, callback_goalPosition)

        ###### Publishers
        # self.publisher_gate_mode = self.session.declare_publisher(self.topic_prefix + SET_GATE_MODE_KEY_EXPR)
        self.publisher_goal = self.session.declare_publisher(self.topic_prefix + SET_GOAL_KEY_EXPR)

        ### Service
        ###### Publishers
        self.publisher_engage = self.session.declare_publisher(self.service_prefix + SET_ENGAGE_KEY_EXPR)


    def setGoal(self, lat, lon):
        coordinate = self.projector.forward(GPSPoint(float(lat), float(lon), 0))
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
        
    def returnGoalPose(self): ### TODO
        goalPoseInfo = []
        for scope, vehicle in self.vehicles.items():
            if vehicle.goalValid:
                goalPoseInfo.append(
                    {
                        'name': scope,
                        'lat': vehicle.goalLat,
                        'lon': vehicle.goalLon
                    }
                )
        return goalPoseInfo

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

