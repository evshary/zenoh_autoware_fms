# FMS Backend Contract

A backend = the bits FMS doesn't ship: a simulator (or real car), the Autoware
ROS bringup, and the bridge wiring them to Zenoh. Pick one with `BACKEND=...`
(default `carla`).

```text
backends/
├── README.md      this file
├── carla.sh       carla 0.9.14 + autoware_carla_launch
├── carla.md       carla setup notes
├── zenoh-bridge-ros2dds-conf.json5   per-vehicle bridge config template
│                  (rendered to tmp/bridge_<scope>.json5 at vehicle start)
└── ...            future: awsim.sh, real_vehicle.sh
```

`just up`, `just down`, and `just setup` source the chosen backend
file and call into the functions in §3.

## 1. Runtime contract

The backend's ROS environment must publish the topics/services FMS reads
and subscribe to the ones FMS writes. The authoritative list is the
ros2dds bridge whitelist (this repo's
`backends/zenoh-bridge-ros2dds-conf.json5`, rendered per vehicle and
injected via `ZENOH_BRIDGE_ROS2DDS_CONFIG`); the bridge re-prefixes keys
with `${VEHICLE_NAME}/` on the Zenoh side. FMS's Zenoh session listens on the
endpoint declared in this repo's `config.json5` (default
`tcp/0.0.0.0:7887`) — that's what each vehicle's bridge connects out to —
and itself connects to the sim bridge's plane for the raw sensor keys.

Optionally, the sim side may publish a camera image
(`<scope>/sensing/camera/traffic_light/image_raw`, raw DDS-CDR Image).
api_server's `MJPEG_server` subscribes to it and streams JPEG frames over
the `/video?scope=` WebSocket.

## 2. Build-time contract

Before `just up` runs, the backend must have produced:

| Artifact | Purpose |
|---|---|
| Autoware workspace (reachable `install/setup.bash`) | ROS env |
| `zenoh-bridge-ros2dds` binary | ROS↔Zenoh |
| Sim-side bridge binary (e.g. `zenoh_carla_bridge`) | sim↔ROS |
| Lanelet OSM map | localization + Map View |
| Perception model weights | perception nodes |
| zenohcxx vendor prefix (e.g. `rmw_zenoh_ws`) | `just build-teleop` + in-container teleop builds |
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
| `BACKEND_AUTOWARE_CONTAINER` | per-vehicle Autoware container name prefix (`<prefix>_<scope>`), consumed only inside the backend (`""` if not container-based) |

### Functions

| Function | Caller | Purpose |
|---|---|---|
| `backend_check_runtime_prereqs` | `just up` | bail early if §1/§2 missing |
| `backend_check_bootstrap_prereqs` | `just setup` | bail early on first-build inputs |
| `backend_bootstrap` | `just setup` | one-time build of all artifacts |
| `backend_seed_frontend_assets` | both | ensure the frontend Map View's map is in `frontend/public/` |
| `backend_seed_custom_configs` | `just up` | apply per-deploy overrides (no-op if none) |
| `backend_export_runtime_flags` | `just up` | export backend-specific runtime env for the FMS services (carla: none); `REACT_APP_*` come from `env.sh` via `just run` |
| `backend_start_sim` | `just up` | start sim (no-op for real cars) |
| `backend_load_world` | `just up` | load the sim world once (vehicles attach to it) |
| `backend_start_bridge` | `just up` | start sim↔ROS bridge (no-op for real cars) |
| `backend_start_ego` | `just up vehicle`, `just up --ros` | spawn one vehicle's ego + sensors |
| `backend_start_autoware` | `just up vehicle`, `just up --ros` | start one vehicle's Autoware bringup |
| `backend_exec_in_ros [-d] <cmd>` | `just up --ros` | run `cmd` in the backend's ROS shell; `-d` = detached |
| `backend_stop` | `just up`, `just down` | stop sim/bridge/egos/autoware |
| `backend_stop_vehicle` | `just down vehicle` | stop one vehicle, leave the rest up |

### Helpers the justfile already provides

`msg "..."`, `warn "..."`, `die "..."`, `have <cmd>`, `wait_for <label> <timeout> <cmd>`, `run_steps "${STEPS[@]}"`, `skip_if_present <label> <check> <cmd>`, `valid_scope <scope>`, `plane_doctor`.

### Not the backend's job

- `external/autoware_manual_control` (FMS submodule)
- `api_server` (uvicorn)
- frontend (npm)
- the per-scope fleet teleops (spawned by the api's FleetManager)

## 4. Lifecycle (justfile-driven)

`just up fms` (precondition: `backend_check_runtime_prereqs`):

```text
cleanup_previous       backend_stop + pkill leftovers
start_simulator        backend_start_sim + backend_seed_custom_configs
backend_load_world
backend_start_bridge
start_fms_services     backend_seed_frontend_assets
                       backend_export_runtime_flags
                       just run (under setsid + nohup; PG → logs/just.pid)
plane_check            plane_doctor (flag stray zenoh clients)
```

`just up vehicle <scope>`: `backend_start_ego` + `backend_start_autoware`;
the teleop is attached later from the web UI (FleetManager spawn).

`just up --ros` (single vehicle, ROS transport): the fms steps (minus the
plane check) plus `backend_start_ego v1`, `backend_start_autoware`, and an
in-container `zenoh_control` built and launched via `backend_exec_in_ros`
before the FMS services start.

At runtime each step is banner-printed as `[i/N]` by `run_steps`; the
counts come from the `STEPS` array, so adding or removing a step
renumbers automatically.

`just down`: stop FMS pieces → `backend_stop`; `just down vehicle <scope>`:
`backend_stop_vehicle` + that scope's host teleop.

`just setup`:

```text
prerequisite.sh                            host deps + uv sync + npm install
check_host_tools                           + backend_check_bootstrap_prereqs
git submodule update --init --recursive
backend_bootstrap                          (the heavy build)
just build-teleop                          operator-side fleet teleop binary (ROS-free)
backend_seed_frontend_assets
```

## 5. Adding a backend

1. Copy `carla.sh`.
2. Implement §3.
3. Write `<name>.md` with the prereqs.
4. `BACKEND=<name> just up`.

If something FMS needs isn't covered here, update this file rather than
papering over it inside the backend script.
