import zenoh
import time
from dataclasses import dataclass
from pycdr2 import IdlStruct
from pycdr2.types import float32, float64, sequence, array
from zenoh_ros_type.rcl_interfaces import Time
from zenoh_ros_type.common_interfaces.std_msgs import Header
from zenoh_ros_type.common_interfaces import Point, Twist, Vector3

from lanelet2.projection import UtmProjector
from lanelet2.io import Origin
from lanelet2.core import BasicPoint3d, GPSPoint

import struct

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

class PoseServer():
    def __init__(self, session, scope, use_bridge_ros2dds=False):
        ### Information
        self.session = session
        self.scope = scope

        self.lat = 0.0
        self.lon = 0.0

        self.positionX = 0.0
        self.positionY = 0.0

        self.topic_prefix = scope if use_bridge_ros2dds else scope + '/rt'
        self.service_prefix = scope if use_bridge_ros2dds else scope + '/rq'

        def callback_position(sample):
            print("Got message of kinematics of vehicle")
            # print("size of the message (bytes) ", struct.calcsize(sample.payload))
            print(sample.payload)
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

        ### Service
        ###### Publishers
        self.publisher_engage = self.session.declare_publisher(self.service_prefix + SET_ENGAGE_KEY_EXPR)
    
    def transform(self, originX=0.0, originY=0.0):
        projector = UtmProjector(Origin(originX, originY))
        gps = projector.reverse(BasicPoint3d(self.positionX, self.positionY, 0.0))
        self.lat = gps.lat
        self.lon = gps.lon
        return

if __name__ == "__main__":
    session = zenoh.open()
    mc = PoseServer(session, 'v1')
    import time
    while True:
        time.sleep(1)
    # msg = VehicleKinematics()