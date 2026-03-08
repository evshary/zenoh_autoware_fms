import time
from threading import Event, Thread

import zenoh
from zenoh_ros_type.autoware_adapi_msgs import ChangeOperationModeResponse, Gear, VehicleKinematics, VehicleStatus
from zenoh_ros_type.autoware_msgs import Control, GearCommand, Lateral, Longitudinal
from zenoh_ros_type.rcl_interfaces import Time
from zenoh_ros_type.rmw_zenoh import Attachment, Empty
from zenoh_ros_type.tier4_autoware_msgs import GateMode

GET_VEHICLE_STATUS_KEY_EXPR = '/api/vehicle/status'
GET_VEHICLE_KINEMATICS_KEY_EXPR = '/api/vehicle/kinematics'
SET_REMOTE_MODE_KEY_EXPR = '/api/operation_mode/change_to_remote'

### TODO: Should be replaced by ADAPI
SET_GATE_MODE_KEY_EXPR = '/control/gate_mode_cmd'
SET_CONTROL_KEY_EXPR = '/external/selected/control_cmd'
SET_GEAR_KEY_EXPR = '/external/selected/gear_cmd'


class ManualController:
    def __init__(self, session, scope, use_bridge_ros2dds=True):
        ### Information
        self.session = session
        self.scope = scope
        self.use_bridge_ros2dds = use_bridge_ros2dds

        self.end_event = Event()

        self.current_velocity = 0
        self.current_gear = 'NONE'
        self.current_steer = 0

        self.target_velocity = 0
        self.target_angle = 0

        self.prefix = scope if use_bridge_ros2dds else scope + '/*'
        self.postfix = '' if use_bridge_ros2dds else '/**'

        def callback_status(sample):
            data = VehicleStatus.deserialize(sample.payload.to_bytes())
            gear_val = data.gear.status
            self.current_gear = Gear.STATUS(gear_val).name
            self.current_steer = data.steering_tire_angle

        def callback_kinematics(sample):
            data = VehicleKinematics.deserialize(sample.payload.to_bytes())
            self.current_velocity = data.twist.twist.twist.linear.x

        ### Topics
        ###### Subscribers
        self.subscriber_status = self.session.declare_subscriber(self.prefix + GET_VEHICLE_STATUS_KEY_EXPR + self.postfix, callback_status)
        self.subscriber_kinematics = self.session.declare_subscriber(
            self.prefix + GET_VEHICLE_KINEMATICS_KEY_EXPR + self.postfix, callback_kinematics
        )
        ###### Publishers
        self.publisher_gate_mode = self.session.declare_publisher(self.prefix + SET_GATE_MODE_KEY_EXPR + self.postfix)
        self.publisher_gear = self.session.declare_publisher(self.prefix + SET_GEAR_KEY_EXPR + self.postfix)
        self.publisher_control = self.session.declare_publisher(self.prefix + SET_CONTROL_KEY_EXPR + self.postfix)

        if not use_bridge_ros2dds:
            self.attachment_gate_mode = Attachment()
            self.attachment_gear = Attachment()
            self.attachment_control = Attachment()
            self.attachment_remote_mode = Attachment()

        ### Gear command stamp
        now = time.time()
        self.gear_stamp = Time(sec=int(now), nanosec=int((now - int(now)) * 1e9))

        ### Control command
        now = time.time()
        self.control_command = Control(
            stamp=Time(sec=int(now), nanosec=int((now - int(now)) * 1e9)),
            control_time=Time(sec=0, nanosec=0),
            lateral=Lateral(
                stamp=Time(sec=0, nanosec=0),
                control_time=Time(sec=0, nanosec=0),
                steering_tire_angle=0,
                steering_tire_rotation_rate=0,
                is_defined_steering_tire_rotation_rate=False,
            ),
            longitudinal=Longitudinal(
                stamp=Time(sec=0, nanosec=0),
                control_time=Time(sec=0, nanosec=0),
                velocity=0,
                acceleration=0,
                jerk=0,
                is_defined_acceleration=False,
                is_defined_jerk=False,
            ),
        )

        ### Startup external control
        self.publisher_gate_mode.put(
            GateMode(data=GateMode.DATA['EXTERNAL'].value).serialize(),
            attachment=None if self.use_bridge_ros2dds else self.attachment_gate_mode.serialize(),
        )

        # Ensure Autoware receives the gate mode change before the operation mode change
        time.sleep(1)
        replies = self.session.get(
            self.prefix + SET_REMOTE_MODE_KEY_EXPR + self.postfix,
            payload=Empty().serialize(),
            attachment=None if self.use_bridge_ros2dds else self.attachment_remote_mode.serialize(),
        )
        for reply in replies:
            try:
                print(">> Received ('{}': {})".format(reply.ok.key_expr, ChangeOperationModeResponse.deserialize(reply.ok.payload.to_bytes())))
            except Exception as e:
                print(f'Failed to handle response: {e}')

        ### Create new thread to send control command
        self.thread = Thread(target=self.pub_control)
        self.thread.start()

    def stop_teleop(self):
        self.update_control_command(0, 0)
        self.end_event.set()
        self.thread.join()

    def pub_gear(self, gear):
        gear_val = GearCommand.COMMAND[gear.upper()].value
        self.gear_stamp.nanosec += 1
        self.publisher_gear.put(
            GearCommand(stamp=Time(sec=self.gear_stamp.sec, nanosec=self.gear_stamp.nanosec), command=gear_val).serialize(),
            attachment=None if self.use_bridge_ros2dds else self.attachment_gear.serialize(),
        )

    def update_control_command(self, velocity, angle):
        if velocity is not None:
            self.target_velocity = velocity
        if angle is not None:
            self.target_angle = angle

    def pub_control(self):
        while not self.end_event.is_set():
            ### Considering gear with velocity
            if self.current_gear.upper() == 'REVERSE':
                _real_target_speed = self.target_velocity * (-1)
            else:
                _real_target_speed = self.target_velocity

            ### Calculate acceleration
            acceleration = self.target_velocity - abs(self.current_velocity)
            if acceleration > 1.0:
                acceleration = 1.0
            elif acceleration < -1.0:
                acceleration = -1.0

            ### Steering angle
            self.control_command.lateral.steering_tire_angle = self.target_angle

            ### Pub control
            self.control_command.longitudinal.velocity = _real_target_speed
            self.control_command.longitudinal.acceleration = acceleration
            self.control_command.stamp.nanosec += 1
            self.publisher_control.put(
                self.control_command.serialize(), attachment=None if self.use_bridge_ros2dds else self.attachment_control.serialize()
            )

            ### Set interval
            time.sleep(0.33)


if __name__ == '__main__':
    conf = zenoh.Config.from_file('config.json5')
    session = zenoh.open(conf)
    mc = ManualController(session, 'v1')

    while True:
        c = input()
        if c == 'gear':
            gear = input()
            mc.pub_gear(gear)
        elif c == 'speed':
            speed = input()
            mc.update_control_command(float(speed))
        elif c == 'new':
            mc.stop_teleop()
            mc = ManualController(session, 'v1')
        else:
            mc.stop_teleop()
            break
