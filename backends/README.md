# FMS Backend Contract

A backend = the bits FMS doesn't ship: a simulator (or real car), the Autoware
ROS bringup, and the bridge wiring them to Zenoh. Pick one with `BACKEND=...`
(default `carla`).

```
backends/
├── README.md      this file
├── carla.sh       carla 0.9.14 + autoware_carla_launch
├── carla.md       carla setup notes
└── ...            future: awsim.sh, real_vehicle.sh
```

`prepare_env.sh`, `shutdown_env.sh`, and `bootstrap.sh` source the chosen
file and call into the functions in §3.

## 1. Runtime contract

What the running stack must expose for FMS to work end-to-end.

### 1.1 ROS 2 topics (ego POV)

The ros2dds bridge re-publishes these into Zenoh under `${VEHICLE_NAME}/`.

| Direction | Topic | Used by |
|---|---|---|
| pub | `/vehicle/status/velocity_status` | HUD speedometer |
| pub | `/vehicle/status/gear_status` | HUD gear |
| pub | `/vehicle/status/steering_status` | HUD steering |
| pub | `/api/operation_mode/state` | gate / engage state |
| pub | `/api/external/get/cpu_usage` | health |
| pub | `/api/external/get/vehicle/status` | health |
| pub | `/api/vehicle/kinematics` | Map View pose |
| pub | `/api/routing/route` | Map View goal |
| sub | `/external/selected/control_cmd` | teleop |
| sub | `/control/command/gear_cmd` | gear shift |
| sub | `/control/gate_mode_cmd` | gate AUTO/EXTERNAL |
| sub | `/external/remote/heartbeat` | keeps gate engaged |
| sub | `/api/external/set/command/remote/shift` | external shift |

### 1.2 ROS 2 services (ADAPI)

| Service | Caller |
|---|---|
| `/api/operation_mode/change_to_remote` | `/teleop/startup` |
| `/api/routing/set_route_points` | Map View "Set Goal" |
| `/api/routing/clear_route` | Map View "Clear" |
| `/api/operation_mode/change_to_autonomous` | (reserved) |

### 1.3 Zenoh ros2dds bridge

- listens on `tcp/127.0.0.1:7447` (or anywhere api_server's session can reach)
- whitelists everything in §1.1 and §1.2
- prefixes keys with `${VEHICLE_NAME}/` (so `/vehicle/status/velocity_status` → `${VEHICLE_NAME}/vehicle/status/velocity_status`)

### 1.4 Camera (optional)

A backend may publish MJPEG on a host port; api_server proxies it via
`mjpeg_host` / `mjpeg_port` returned from `/teleop/startup`.

## 2. Build-time contract

Before `prepare_env.sh` runs, the backend must have produced:

| Artifact | Purpose |
|---|---|
| Autoware workspace (reachable `install/setup.bash`) | ROS env |
| `zenoh-bridge-ros2dds` binary | ROS↔Zenoh |
| Sim-side bridge binary (e.g. `zenoh_carla_bridge`) | sim↔ROS |
| Lanelet OSM map | localization + Map View |
| Perception model weights | perception nodes |
| DDS env config | usually `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` + `ROS_LOCALHOST_ONLY=1` |
| Container image(s) | runtime, if Docker-based |

Carla specifics: see `carla.md`.

## 3. Bash function contract

The backend file must define these. The orchestrator sources it and calls
them.

### Variables

| Name | Purpose |
|---|---|
| `BACKEND_NAME` | display string |
| `BACKEND_AUTOWARE_CONTAINER` | container to docker-exec into (`""` if not container-based) |

### Functions

| Function | Caller | Purpose |
|---|---|---|
| `backend_check_runtime_prereqs` | `prepare_env.sh` | bail early if §1/§2 missing |
| `backend_check_bootstrap_prereqs` | `bootstrap.sh` | bail early on first-build inputs |
| `backend_bootstrap` | `bootstrap.sh` | one-time build of all artifacts |
| `backend_seed_frontend_assets` | both | mirror map etc. into `frontend/public/` |
| `backend_seed_custom_configs` | `prepare_env.sh` | apply per-deploy overrides (no-op if none) |
| `backend_export_runtime_flags` | `prepare_env.sh` | export backend-specific runtime env (e.g. `USE_BRIDGE_ROS2DDS`); `REACT_APP_*` come from `env.sh` via `just run` |
| `backend_start_sim` | `prepare_env.sh` | start sim (no-op for real cars) |
| `backend_start_bridge` | `prepare_env.sh` | start sim↔ROS bridge (no-op for real cars) |
| `backend_start_autoware` | `prepare_env.sh` | start Autoware bringup |
| `backend_wait_ready` | `prepare_env.sh` (optional) | wait for `is_remote_mode_available: true` |
| `backend_exec_in_ros [-d] <cmd>` | `prepare_env.sh` | run `cmd` in the backend's ROS shell; `-d` = detached |
| `backend_stop` | `prepare_env.sh`, `shutdown_env.sh` | stop sim/bridge/autoware |

### Helpers the orchestrator already provides

`msg "..."`, `warn "..."`, `die "..."`, `have <cmd>`.

### Not the backend's job

- `external/autoware_manual_control` (FMS submodule)
- `api_server` (uvicorn)
- frontend (npm)
- seeding `teleop_config.yaml` from `.example`
- building `zenoh-fms-engine` (FMS Dockerfile)

## 4. Lifecycle (orchestrator-driven)

`prepare_env.sh` (precondition: `backend_check_runtime_prereqs`):

```
[1/6]  cleanup_previous       backend_stop + pkill leftovers
[2/6]  start_simulator        backend_start_sim + backend_seed_custom_configs
[3/6]  backend_start_bridge
[4/6]  backend_start_autoware
[5/6]  start_manual_control   colcon build + ros2 run remote_control
[6/6]  start_fms_services     backend_seed_frontend_assets
                              backend_export_runtime_flags
                              just run (under setsid + nohup; PG → logs/just.pid)
```

Numbering is generated by `lib/orchestrator.sh::run_steps` from a `STEPS`
array — adding/removing a step renumbers automatically.

`shutdown_env.sh`: stop FMS pieces → `backend_stop`.

`bootstrap.sh`:

```
backend_check_bootstrap_prereqs
git submodule init
build zenoh-fms-engine image
backend_bootstrap                          (the heavy build)
backend_seed_frontend_assets
uv sync
npm install
```

## 5. Adding a backend

1. Copy `carla.sh`.
2. Implement §3.
3. Write `<name>.md` with the prereqs.
4. `BACKEND=<name> bash prepare_env.sh`.

If something FMS needs isn't covered here, update this file rather than
papering over it inside the backend script.
