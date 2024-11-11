import time
from threading import Event, Thread

import zenoh
from zenoh_ros_type.autoware_adapi_msgs import ChangeOperationMode
from zenoh_ros_type.autoware_msgs import Control, Lateral, Longitudinal
from zenoh_ros_type.rcl_interfaces import Time
from zenoh_ros_type.tier4_autoware_msgs import GateMode, GearShift, GearShiftStamped, VehicleStatusStamped

GET_STATUS_KEY_EXPR = '/api/external/get/vehicle/status'
SET_REMOTE_MODE_KEY_EXPR = '/api/operation_mode/change_to_remote'
SET_GEAR_KEY_EXPR = '/api/external/set/command/remote/shift'

### TODO: Should be replaced by ADAPI
SET_GATE_MODE_KEY_EXPR = '/control/gate_mode_cmd'
SET_CONTROL_KEY_EXPR = '/external/selected/control_cmd'


class ManualController:
    def __init__(self, session, scope, use_bridge_ros2dds=True):
        ### Information
        self.session = session
        self.scope = scope

        self.end_event = Event()

        self.current_velocity = 0
        self.current_gear = 'NONE'
        self.current_steer = 0

        self.target_velocity = 0
        self.target_angle = 0

        self.topic_prefix = scope if use_bridge_ros2dds else scope + '/rt'

        def callback_status(sample):
            data = VehicleStatusStamped.deserialize(sample.payload.deserialize(bytes))
            self.current_velocity = data.status.twist.linear.x
            gear_val = data.status.gear_shift.data
            self.current_gear = GearShift.DATA(gear_val).name
            self.current_steer = data.status.steering.data

        ### Topics
        ###### Subscribers
        self.subscriber_status = self.session.declare_subscriber(self.topic_prefix + GET_STATUS_KEY_EXPR, callback_status)

        ###### Publishers
        self.publisher_gate_mode = self.session.declare_publisher(self.topic_prefix + SET_GATE_MODE_KEY_EXPR)
        self.publisher_gear = self.session.declare_publisher(self.topic_prefix + SET_GEAR_KEY_EXPR)
        self.publisher_control = self.session.declare_publisher(self.topic_prefix + SET_CONTROL_KEY_EXPR)

        ### Control command
        self.control_command = Control(
            stamp=Time(sec=0, nanosec=0),
            control_time=Time(sec=0, nanosec=0),
            lateral=Lateral(
                stamp=Time(sec=0, nanosec=0),
                control_time=Time(sec=0, nanosec=0),
                steering_tire_angle=0, 
                steering_tire_rotation_rate=0,
                is_defined_steering_tire_rotation_rate=False),
            longitudinal=Longitudinal(
                stamp=Time(sec=0, nanosec=0),
                control_time=Time(sec=0, nanosec=0),
                velocity=0, 
                acceleration=0, 
                jerk=0,
                is_defined_acceleration=False,
                is_defined_jerk=False),
        )

        ### Startup external control
        self.publisher_gate_mode.put(GateMode(data=GateMode.DATA['EXTERNAL'].value).serialize())
        
        # Ensure Autoware receives the gate mode change before the operation mode change
        time.sleep(1)
        
        replies = self.session.get(self.topic_prefix + SET_REMOTE_MODE_KEY_EXPR)
        for reply in replies:
            # TODO: Handle service payload deserialize error
            print(f"Received data (bytes): {reply.ok.payload.deserialize(bytes)}")
            payload = reply.ok.payload.deserialize(bytes)[-4:]+reply.ok.payload.deserialize(bytes)[:-4]
            print(f"Modified payload (bytes): {payload}")

            try:
                # print(">> Received ('{}': {})".format(reply.ok.key_expr, ChangeOperationMode.deserialize(reply.ok.payload.deserialize(bytes))))
                print(">> Received ('{}': {})".format(reply.ok.key_expr, ChangeOperationMode.deserialize(payload)))            
            except:
                print(">> Received (ERROR: '{}')".format(reply.err.payload.deserialize(bytes)))
                raise


        ### Create new thread to send control command
        self.thread = Thread(target=self.pub_control)
        self.thread.start()

    def stop_teleop(self):
        self.update_control_command(0, 0)
        self.end_event.set()
        self.thread.join()

    def pub_gear(self, gear):
        gear_val = GearShift.DATA[gear.upper()].value
        self.publisher_gear.put(GearShiftStamped(stamp=Time(sec=0, nanosec=0), gear_shift=GearShift(data=gear_val)).serialize())

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
            self.control_command.longitudinal.velocity = self.target_velocity
            self.control_command.longitudinal.acceleration = acceleration
            self.control_command.stamp.nanosec += 1
            self.publisher_control.put(self.control_command.serialize())

            ### Set interval
            time.sleep(0.33)


if __name__ == '__main__':
    session = zenoh.open()
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
