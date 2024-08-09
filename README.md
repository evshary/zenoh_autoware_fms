# zenoh_autoware_fms

The project is the FMS (fleet management system) prototype of Autoware based on Zenoh.

![FMS Architecture](resource/Autoware_FMS_Zenoh_Architecture.svg)

## Usage

### Basic test

- Install prerequisite

```shell
./prerequisite.sh
```

- Run Web Server & API Server

```shell
# Before the following steps, please source ROS 2 environment
source env.sh
./run_server.sh
```

- You can use environment [here](https://github.com/evshary/zenoh_demo_docker_env/tree/main/autoware_multiple_fms) to test FMS
  - Remember to change the IP in `docker-compose.yml` to FMS IP.

### Integration with Carla

Here is [the tutorial](https://autoware-carla-launch.readthedocs.io/en/latest/scenarios/fms.html) how to run FMS with Carla.

## Development

- API Server: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Zenoh Listen Port: TCP/7887

## Project

Please check our roadmap in [GitHub Project](https://github.com/users/evshary/projects/2)

## For Developers

You can use pre-commit and Ruff to have correct Python format

```shell
python3 -m pip install pre-commit ruff
pre-commit install --install-hooks
```

## Autoware API

### Topic

| Category | Name                                    | Type                                                                 | Description                             | Note                                                           |
| :------- | :-------------------------------------- | :------------------------------------------------------------------- | :-------------------------------------- | :------------------------------------------------------------- |
| Pose     | /api/vehicle/kinematics                 | autoware_adapi_v1_msgs/msg/VehicleKinematics                         | Get vehicle kinematics                  |                                                                |
| Pose     | /api/routing/route                      | autoware_adapi_v1_msgs/msg/Route                                     | Get the route and the goal position     |                                                                |
| Pose     | /planning/mission_planning/goal         | geometry_msgs/msg/PoseStamped                                        | Set the goal position and orientation   | AWS has't provided API for setting goal                        |
| Pose     | /control/gate_mode_cmd                  | tier4_control_msgs/msg/GateMode                                      | Set the gate mode to AUTO               | To be replaced by /api/operation_mode/enable_autoware_control  |
| Status   | /api/external/get/cpu_usage             | tier4_autoware_msgs/tier4_external_api_msgs/msg/CpuUsage             | Get the current CPU usage statistics    |                                                                |
| Status   | /api/external/get/vehicle/status        | tier4_autoware_msgs/tier4_external_api_msgs/msg/VehicleStatusStamped | Get gear shift and turn signal          |                                                                |
| Teleop   | /api/external/get/vehicle/status        | tier4_autoware_msgs/tier4_external_api_msgs/msg/VehicleStatusStamped | Get gear shift and turn signal          |                                                                |
| Teleop   | /control/gate_mode_cmd                  | tier4_control_msgs/msg/GateMode                                      | Set the gate mode to External           | To be replaced by /api/operation_mode/disable_autoware_control |
| Teleop   | /api/external/set/command/remote/shift  | tier4_autoware_msgs/tier4_external_api_msgs/msg/GearShiftStamped     | Set gear shift from FMS                 |                                                                |
| Teleop   | /external/selected/control_cmd          | autoware_auto_control_msgs/AckermannControlCommand                   | Set longitudinal speed and acceleration | AWS has't provided API for setting speed                       |
| Camera   | /sensing/camera/traffic_light/image_raw | sensor_msgs/msg/Image                                                | Get camera image                        | AWS has't provided API for streaming camera image              |

### Service

| Category | Name                                     | Type                                         | Description                             |
| :------- | :--------------------------------------- | :------------------------------------------- | :-------------------------------------- |
| Pose     | /api/operation_mode/change_to_autonomous | autoware_adapi_v1_msgs/srv/ChangeOperionMode | Change the operation mode to autonomous |
| Teleop   | /api/operation_mode/change_to_remote     | autoware_adapi_v1_msgs/srv/ChangeOperionMode | Change the operation mode to remote     |
