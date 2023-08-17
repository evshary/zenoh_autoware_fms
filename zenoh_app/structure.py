from dataclasses import dataclass
from pycdr2 import IdlStruct,Enum
from pycdr2.types import int8, uint8, int32, int64, uint32, uint64, float32, float64, sequence
from zenoh_ros_type import Time, Vector3

@dataclass
class CpuStatus(IdlStruct, typename="CpuStatus"):
    class STATUS(Enum):
        OK = 0
        HIGH_LOAD = 1
        VERY_HIGH_LOAD = 2
        STALE = 3
    status: uint8
    total: float32
    usr: float32
    nice: float32
    sys: float32
    idle: float32

@dataclass
class cpu_usage(IdlStruct, typename="cpu_usage"):
    stamp: Time
    all: CpuStatus
    cpus: sequence[CpuStatus]

@dataclass
class Twist(IdlStruct, typename="Twist"):
    linear: Vector3
    angular: Vector3

@dataclass
class Steering(IdlStruct, typename="Steering"):
    data: float32

@dataclass
class TurnSignal(IdlStruct, typename="TurnSignal"):
    class TURN(Enum):
        NONE = 0
        LEFT = 1
        RIGHT = 2
        HAZARD = 3
    data: uint8

@dataclass
class GearShift(IdlStruct, typename="GearShift"):
    class GEAR(Enum):
        NONE = 0
        PARKING = 1
        REVERSE = 2
        NEUTRAL = 3
        DRIVE = 4
        LOW = 5
    data: uint8

@dataclass
class VehicleStatus(IdlStruct, typename="VehicleStatus"):
    twist: Twist
    steering: Steering
    turn_signal: TurnSignal
    gear_shift: GearShift

@dataclass
class vehicle_status(IdlStruct, typename="vehicle_status"):
    stamp: Time
    status: VehicleStatus

@dataclass
class ControlCommand(IdlStruct, typename="ControlCommand"):
    steering_angle: float64
    steering_angle_velocity: float64
    throttle: float64
    brake: float64

@dataclass
class ControlCommandStamped(IdlStruct, typename="ControlCommandStamped"):
    stamp: Time
    control: ControlCommand

@dataclass
class GearShiftStamped(IdlStruct, typename="GearShiftStamped"):
    stamp: Time
    gear_shift: GearShift

@dataclass
class TurnSignalStamped(IdlStruct, typename="GearShiftStamped"):
    stamp: Time
    turn_signal: TurnSignal
    
@dataclass
class GateMode(IdlStruct, typename="GateMode"):
    class MODE(Enum):
        AUTO = 0
        EXTERNAL = 1
    data: uint8

@dataclass
class AckermannLateralCommand(IdlStruct, typename="AckermannLateralCommand"):
    stamp: Time
    steering_tire_angle: float32
    steering_tire_rotation_rate: float32

@dataclass
class LongitudinalCommand(IdlStruct, typename="LongitudinalCommand"):
   stamp: Time
   speed: float32
   acceleration: float32
   jerk: float32

@dataclass
class AckermannControlCommand(IdlStruct, typename="AckermannControlCommand"):
    stamp: Time
    lateral: AckermannLateralCommand
    longitudinal: LongitudinalCommand

@dataclass
class ServiceHeader(IdlStruct, typename="ServiceHeader"):
    guid: int64
    seq: uint64

@dataclass
class EngageReq(IdlStruct, typename="EngageReq"):
    header: ServiceHeader
    engage: bool