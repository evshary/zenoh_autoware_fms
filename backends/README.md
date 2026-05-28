# FMS Backend Contract

A backend = the bits FMS doesn't ship: a simulator (or real car), the Autoware
ROS bringup, and the bridge wiring them to Zenoh. Pick one with `BACKEND=...`
(default `carla`).

```text
backends/
├── README.md      this file
├── carla.sh       carla 0.9.14 + autoware_carla_launch
├── carla.md       carla setup notes
└── ...            future: awsim.sh, real_vehicle.sh
```

`just up`, `just down`, and `just setup` source the chosen backend
file and call into the functions in §3.

## 1. Runtime contract

The backend's ROS environment must publish the topics/services FMS reads
and subscribe to the ones FMS writes. The authoritative list is the
ros2dds bridge whitelist (`zenoh-bridge-ros2dds-conf.json5` in the sibling
`autoware_carla_launch` tree); the bridge re-prefixes keys with
`${VEHICLE_NAME}/` on the Zenoh side. FMS's Zenoh router listens on the
endpoint declared in this repo's `config.json5` (default
`tcp/0.0.0.0:7887`) — that's what the bridge connects out to.

Optionally, a backend may publish a ROS camera image topic
(e.g. `/sensing/camera/traffic_light/image_raw`, whitelisted under
`/sensing/camera/.*`). api_server's `MJPEG_server` subscribes via Zenoh
and re-serves the frames as HTTP MJPEG at the `mjpeg_host:mjpeg_port`
returned from `/teleop/startup`.

## 2. Build-time contract

Before `just up` runs, the backend must have produced:

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

The backend file must define these. The justfile recipes source it and call
them.

### Variables

| Name | Purpose |
|---|---|
| `BACKEND_NAME` | display string |
| `BACKEND_AUTOWARE_CONTAINER` | container to docker-exec into (`""` if not container-based) |

### Functions

| Function | Caller | Purpose |
|---|---|---|
| `backend_check_runtime_prereqs` | `just up` | bail early if §1/§2 missing |
| `backend_check_bootstrap_prereqs` | `just setup` | bail early on first-build inputs |
| `backend_bootstrap` | `just setup` | one-time build of all artifacts |
| `backend_seed_frontend_assets` | both | mirror map etc. into `frontend/public/` |
| `backend_seed_custom_configs` | `just up` | apply per-deploy overrides (no-op if none) |
| `backend_export_runtime_flags` | `just up` | export backend-specific runtime env (e.g. `USE_BRIDGE_ROS2DDS`); `REACT_APP_*` come from `env.sh` via `just run` |
| `backend_start_sim` | `just up` | start sim (no-op for real cars) |
| `backend_start_bridge` | `just up` | start sim↔ROS bridge (no-op for real cars) |
| `backend_start_autoware` | `just up` | start Autoware bringup |
| `backend_wait_ready` | `just up` (optional) | wait for `is_remote_mode_available: true` |
| `backend_exec_in_ros [-d] <cmd>` | `just up` | run `cmd` in the backend's ROS shell; `-d` = detached |
| `backend_stop` | `just up`, `just down` | stop sim/bridge/autoware |

### Helpers the justfile already provides

`msg "..."`, `warn "..."`, `die "..."`, `have <cmd>`.

### Not the backend's job

- `external/autoware_manual_control` (FMS submodule)
- `api_server` (uvicorn)
- frontend (npm)
- seeding `teleop_config.yaml` from `.example`

## 4. Lifecycle (justfile-driven)

`just up` (precondition: `backend_check_runtime_prereqs`):

```text
cleanup_previous       backend_stop + pkill leftovers
start_simulator        backend_start_sim + backend_seed_custom_configs
backend_start_bridge
backend_start_autoware
start_manual_control   colcon build + ros2 run remote_control
start_fms_services     backend_seed_frontend_assets
                       backend_export_runtime_flags
                       just run (under setsid + nohup; PG → logs/just.pid)
```

At runtime each step is banner-printed as `[i/N]` by `run_steps`; the
counts come from the `STEPS` array, so adding or removing a step
renumbers automatically.

`just down`: stop FMS pieces → `backend_stop`.

`just setup`:

```text
backend_check_bootstrap_prereqs
git submodule init
backend_bootstrap                          (the heavy build)
backend_seed_frontend_assets
uv sync
npm install
```

## 5. Adding a backend

1. Copy `carla.sh`.
2. Implement §3.
3. Write `<name>.md` with the prereqs.
4. `BACKEND=<name> just up`.

If something FMS needs isn't covered here, update this file rather than
papering over it inside the backend script.
