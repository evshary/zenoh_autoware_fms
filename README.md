# zenoh_autoware_fms

The project is the FMS (fleet management system) prototype of Autoware based on Zenoh.

![FMS Architecture](resource/Autoware_FMS_Zenoh_Architecture.svg)

```mermaid
sequenceDiagram
Autoware AD API -) zenoh-bridge-ros2dds: vehicle status / sensor data
zenoh-bridge-ros2dds -) Management System: Zenoh messages
Management System -) zenoh-bridge-ros2dds: Zenoh messages
zenoh-bridge-ros2dds -) Autoware AD API: control commands
```

## Usage

### Basic test

- Install prerequisite

```shell
./prerequisite.sh
```

- Run Web Server & API Server

```shell
# Run with rmw_zenoh (without zenoh-bridge-ros2dds)
just run_rmw_zenoh

# Or run with zenoh-bridge-ros2dds
just run_ros2dds
```

- You can use [the environment](https://github.com/evshary/zenoh_demo_docker_env/tree/main/autoware_fms_with_bridge_ros2dds) to test FMS
  - Remember to change the environment `FMS_CONNECTION`, which means FMS IP.

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
uv run pre-commit install --install-hooks
```

## Autoware Topics & Services in Use

Below is the list of topics and services currently in use in the FMS:

### Topic

| Category | Name                                         | Type                                         | Description                                | Note               |
| :------- | :------------------------------------------- | :------------------------------------------- | :----------------------------------------- | :----------------- |
| Pose     | /api/vehicle/kinematics                      | autoware_adapi_v1_msgs/msg/VehicleKinematics | Retrieve vehicle kinematics                |                    |
| Pose     | /api/routing/route                           | autoware_adapi_v1_msgs/msg/Route             | Retrieve the route and goal position       |                    |
| Pose     | /control/gate_mode_cmd                       | tier4_control_msgs/msg/GateMode              | Set the gate mode to AUTO                  | No ADAPI available |
| Status   | /system/system_monitor/cpu_monitor/cpu_usage | tier4_external_api_msgs/msg/CpuUsage         | Retrieve current CPU usage statistics      | No ADAPI available |
| Status   | /api/vehicle/status                          | autoware_adapi_v1_msgs/msg/VehicleStatus     | Retrieve gear shift and turn signal status |                    |
| Teleop   | /api/vehicle/status                          | autoware_adapi_v1_msgs/msg/VehicleStatus     | Retrieve gear shift and turn signal status |                    |
| Teleop   | /api/vehicle/kinematics                      | autoware_adapi_v1_msgs/msg/VehicleKinematics | Retrieve vehicle kinematics                |                    |
| Teleop   | /control/gate_mode_cmd                       | tier4_control_msgs/msg/GateMode              | Set the gate mode to External              | No ADAPI available |
| Teleop   | /external/selected/gear_cmd                  | autoware_vehicle_msgs/msg/GearCommand        | Set gear shift from FMS                    | No ADAPI available |
| Teleop   | /external/selected/control_cmd               | autoware_control_msgs/msg/Control            | Set the target speed and steering angle    | No ADAPI available |
| Camera   | /sensing/camera/traffic_light/image_raw      | sensor_msgs/msg/Image                        | Retrieve camera image                      | No ADAPI available |

### Service

| Category | Name                                     | Type                                           | Description                             |
| :------- | :--------------------------------------- | :--------------------------------------------- | :-------------------------------------- |
| Pose     | /api/operation_mode/change_to_autonomous | autoware_adapi_v1_msgs/srv/ChangeOperationMode | Change the operation mode to autonomous |
| Pose     | /api/routing/clear_route                 | autoware_adapi_v1_msgs/srv/ClearRoute          | Clear the currently set route           |
| Pose     | /api/routing/set_route_points            | autoware_adapi_v1_msgs/srv/SetRoutePoints      | Define the route goal and waypoints     |
| Teleop   | /api/operation_mode/change_to_remote     | autoware_adapi_v1_msgs/srv/ChangeOperationMode | Change the operation mode to remote     |
