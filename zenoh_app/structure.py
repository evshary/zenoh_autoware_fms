from dataclasses import dataclass
from pycdr2 import IdlStruct,Enum
from pycdr2.types import int8, uint8, int32, uint32, float32, float64, sequence

@dataclass
class Time(IdlStruct, typename="Time"):
    sec: int32
    nanosec: uint32

@dataclass
class Vector3(IdlStruct, typename="Vector3"):
    x: float64
    y: float64
    z: float64

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
    class SIGNAL(Enum):
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