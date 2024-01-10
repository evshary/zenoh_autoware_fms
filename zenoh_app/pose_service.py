import zenoh
import time
from dataclasses import dataclass
from pycdr2 import IdlStruct
from pycdr2.types import float32, float64, sequence, array
from zenoh_ros_type.rcl_interfaces import Time
from zenoh_ros_type.common_interfaces import Header
from zenoh_ros_type.common_interfaces import Pose, Twist, Vector3

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
class PoseWithCovariance(IdlStruct, typename="PoseWithCovariance"):
    pose: Pose
    covariance: array[float64, 36]

@dataclass
class PoseWithCovarianceStamped(IdlStruct, typename="PoseWithCovarianceStamped"):
    header: Header
    pose: PoseWithCovariance

@dataclass
class TwistWithCovarianceStamped(IdlStruct, typename="TwistWithCovarianceStamped"):
    header: Header
    twist: Twist

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
            data = VehicleKinematics.deserialize(sample.payload)
            self.positionX = data.pose.pose.x
            self.positionY = data.pose.pose.y
            self.transform()

        ### Topics
        ###### Subscribers
        self.subscriber_status = self.session.declare_subscriber(self.topic_prefix + GET_POSE_KEY_EXPR, callback_status)

        ###### Publishers
        # self.publisher_gate_mode = self.session.declare_publisher(self.topic_prefix + SET_GATE_MODE_KEY_EXPR)

        ### Service
        ###### Publishers
        self.publisher_engage = self.session.declare_publisher(self.service_prefix + SET_ENGAGE_KEY_EXPR)
    
    def transform(self):
        pass


if __name__ == "__main__":
    session = zenoh.open()
    mc = PoseServer(session, 'v1')