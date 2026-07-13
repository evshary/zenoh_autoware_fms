# Carla Backend

Wraps Carla 0.9.14 + a sibling clone of `evshary/autoware_carla_launch`.
This is the default; running with no `BACKEND` set picks it.

```bash
just up fms                 # carla (default)
BACKEND=carla just up fms   # explicit
```

This file covers the one-time prereqs that `just setup` can't do for you.

## After setup

- `<workspace>/autoware_carla_launch/` — upstream clone, as-is
  - `install/setup.bash` — colcon-built Autoware workspace
  - `external/zenoh_carla_bridge/target/release/zenoh_carla_bridge` — Rust bridge
  - `external/zenoh-plugin-ros2dds/target/release/zenoh-bridge-ros2dds` — ROS↔Zenoh bridge (run-autoware.sh)
  - `external/zenoh_carla_bridge/carla_agent/.venv/` — Python venv with `carla`
  - `carla_map/Town01/` — lanelet OSM + pointcloud PCD
  - `autoware_data/` — perception weights (~1.5 GB)
  - `rmw_zenoh_ws/install/zenoh_cpp_vendor/` — zenohcxx vendor prefix consumed
    by `just build-teleop` and the in-container teleop build
  - `rust/`, `poetry/`, `pyenv/` — toolchains
- `<workspace>/carla-0.9.14/` — Carla binary
- Two local Docker images:
  - `zenoh-carla-bridge-1.5.0`
  - `zenoh-autoware-1.5.0`

Disk: ~14 GB (tree + images) + ~7 GB Carla.

## Layout

```text
<workspace>/
├── zenoh_autoware_fms/    ← this repo (PROJECT_ROOT)
├── autoware_carla_launch/ ← evshary/autoware_carla_launch sibling clone
└── carla-0.9.14/          ← Carla binary, you provide
```

Sibling paths are hard-coded; override via env vars:

- `BACKEND_ROOT` (default: `${PROJECT_ROOT}/../autoware_carla_launch`)
- `CARLA_BIN` (default: `${PROJECT_ROOT}/../carla-0.9.14/CarlaUE4.sh`)

## Prereqs

`just setup` is zero-touch — it auto-clones `autoware_carla_launch`, builds
the two upstream Docker images, and (optionally) downloads the Carla binary.
**You only need a host with the tools below and disk for the
artifacts.**

| Need | Detail |
|---|---|
| Host tools | `docker`, `git`, `uv`, `node`, `npm`, `just`, `curl`, `colcon`; `prerequisite.sh` uses `sudo` apt for `parallel`, `build-essential`, `cmake`, `libyaml-dev`, `nlohmann-json3-dev` and installs `colcon` via `uv tool install`. `just setup` checks the tool list and bails if any is missing. |
| NVIDIA GPU + driver | The Autoware bringup needs it; the container gets the GPU via `docker --gpus`, CDI, or direct `/dev/nvidia*` + driver-lib binds — `just up vehicle` dies if none works. |
| Disk | ~14 GB (autoware_carla_launch tree + 2 images + perception weights) — plus ~7 GB if Carla is auto-downloaded. |
| Network | ~6 GB pull (images, perception models). Add ~7 GB if `CARLA_AUTODOWNLOAD=1`. |

## Setup

```bash
cd zenoh_autoware_fms
just setup
CARLA_AUTODOWNLOAD=1 just setup
```

What it does (idempotent — re-runs skip done work):

1. Host prerequisites (`prerequisite.sh`) — system packages (incl. `build-essential`, `cmake`, `libyaml-dev`, `nlohmann-json3-dev`), `uv sync`, `colcon` via `uv tool`, `npm install`
2. Host tooling check (docker / git / uv / node / npm / just / colcon) + backend bootstrap prereqs
3. FMS submodule init (`git submodule update --init --recursive`)
4. **Backend bootstrap** (the heavy part):
   - clone `autoware_carla_launch` sibling (if missing)
   - init backend submodules
   - build `zenoh-carla-bridge-1.5.0` image (if missing) — ~20-40 min
   - build `zenoh-autoware-1.5.0` image (if missing) — ~20-40 min
   - download + extract Carla 0.9.14 (only if `CARLA_AUTODOWNLOAD=1` and missing)
   - install Rust toolchain into the bridge tree
   - cargo build `zenoh_carla_bridge`
   - cargo build `zenoh-bridge-ros2dds` (run-autoware.sh requires it)
   - install poetry/pyenv (`virtualenv<21` pinned for the Python 3.8 venvs) + carla_agent venv
   - download Town01 lanelet map + perception weights
   - colcon build the Autoware ROS workspace
   - build `rmw_zenoh_ws` `zenoh_cpp_vendor` (zenohcxx for the teleop builds)
5. Operator-side fleet teleop (`just build-teleop`, ROS-free native build)
6. Frontend Map View lanelet in `frontend/public/` (`download_map.sh`)

First run on a fresh host: ~25–45 min (download-bound). Re-runs: under a minute (everything skips).

If you'd rather position the Carla binary yourself, drop the extracted
tree at `${PROJECT_ROOT}/../carla-0.9.14/` (override with `CARLA_BIN` env
var) before or after `just setup` — the binary is only consumed by
`just up` (`backend_start_sim`).

## Run

```bash
just up fms
just up vehicle v1
# http://localhost:3000
just down
```

## Troubleshooting

### `Carla binary not at <workspace>/carla-0.9.14/CarlaUE4.sh`

The Carla binary step was not done. `just up` warns and skips Carla
startup; Autoware-only flows still work, but you can't drive without Carla.

### `Docker image missing: zenoh-carla-bridge-1.5.0`

`just up` refuses to start; re-run `just setup` to build the image.

### Carla starts but `port 2000 ... TIMEOUT`

Carla took >40 s to come up. Usually one of:

1. **DISPLAY hangs UE4** even with `-RenderOffScreen`. The script wraps
   Carla in `env -u DISPLAY`, so this only bites if you launched it yourself.
2. **GPU driver mismatch.** Carla 0.9.14 / UE4 4.26 wants a working Vulkan.
   RTX 50xx may need newer drivers.

## Known limits

- **Town01 only.** The map path
  `frontend/public/carla_map/Town01/lanelet2_map.osm` is hard-coded. Other
  Towns work in Carla, but you'd need to swap the download script and update
  `REACT_APP_MAP_FILE_PATH`.
- **Carla 0.9.14 only.** PythonAPI ABI shifted in 0.9.15+; the `carla`
  package pinned in `carla_agent`'s poetry venv is 0.9.14-specific.
