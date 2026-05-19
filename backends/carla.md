# Carla Backend

Wraps Carla 0.9.14 + a sibling clone of `Shiritai/autoware_carla_launch`.
This is the default; running with no `BACKEND` set picks it.

```bash
just up                 # carla (default)
BACKEND=carla just up   # explicit
```

This file covers the one-time prereqs that `just setup` can't do for you.

## After setup

- `${WORKSPACE}/autoware_carla_launch/`
  - `install/setup.bash` — colcon-built Autoware workspace
  - `external/zenoh_carla_bridge/target/release/zenoh_carla_bridge` — Rust bridge
  - `external/zenoh_carla_bridge/carla_agent/.venv/` — Python venv with `carla`
  - `carla_map/Town01/` — lanelet OSM + pointcloud PCD
  - `autoware_data/` — perception weights (~1.5 GB)
  - `rust/`, `poetry/`, `pyenv/` — toolchains
- `${WORKSPACE}/carla-0.9.14/` — Carla binary
- Three local Docker images:
  - `zenoh-carla-bridge-1.5.0`
  - `zenoh-autoware-1.5.0`
  - `zenoh-fms-engine:latest` (FMS-built from `zenoh_app/Dockerfile.fms`)

Disk: ~10 GB build artifacts + ~4 GB Carla.

## Layout

```text
<workspace>/
├── zenoh_autoware_fms/    ← this repo (PROJECT_ROOT)
├── autoware_carla_launch/ ← Shiritai/autoware_carla_launch sibling clone
└── carla-0.9.14/          ← Carla binary, you provide
```

Sibling paths are hard-coded; override via env vars:

- `BACKEND_ROOT` (default: `${PROJECT_ROOT}/../autoware_carla_launch`)
- `CARLA_BIN` (default: `${PROJECT_ROOT}/../carla-0.9.14/CarlaUE4.sh`)

## Prereqs

`just setup` is zero-touch — it auto-clones `autoware_carla_launch`, builds
the two upstream Docker images, and (optionally) downloads the Carla
binary. **You only need a host with the tools below and disk for the
artifacts.**

| Need | Detail |
|---|---|
| Host tools | `docker`, `git`, `uv`, `node`, `npm`, `just`. `just setup` checks this list and bails if any is missing. |
| Disk | ~14 GB (autoware_carla_launch tree + 2 images + perception weights) — plus ~4 GB if Carla is auto-downloaded. |
| Network | ~6 GB pull (images, perception models). Add ~4 GB if `CARLA_AUTODOWNLOAD=1`. |

## Setup

```bash
cd zenoh_autoware_fms
just setup
# default: Carla binary stays manual; pass CARLA_AUTODOWNLOAD=1 to grab it too
CARLA_AUTODOWNLOAD=1 just setup
```

What it does (idempotent — re-runs skip done work):

1. Check host tools (docker / git / uv / node / npm / just)
2. FMS submodule init
3. Build `zenoh-fms-engine` image
4. **Backend bootstrap** (the heavy part):
   - clone `autoware_carla_launch` sibling (if missing)
   - build `zenoh-carla-bridge-1.5.0` image (if missing) — ~20-40 min
   - build `zenoh-autoware-1.5.0` image (if missing) — ~20-40 min
   - download + extract Carla 0.9.14 (only if `CARLA_AUTODOWNLOAD=1` and missing)
   - install Rust toolchain into the bridge tree
   - cargo build `zenoh_carla_bridge`
   - install poetry/pyenv + carla_agent venv
   - download Town01 lanelet map + perception weights
   - colcon build the Autoware ROS workspace
5. Mirror lanelet to `frontend/public/`
6. `uv sync`
7. `npm install`

First run on a fresh host: 30–60 min. Re-runs: under a minute (everything skips).

If you'd rather position the Carla binary yourself, drop the extracted
tree at `${PROJECT_ROOT}/../carla-0.9.14/` (override with `CARLA_BIN` env
var) before or after `just setup` — the binary is only consumed by
`just up` (`backend_start_sim`).

## Run

```bash
just up
# http://localhost:3000
just down
```

## Troubleshooting

### `Carla binary not found at /workspace/carla-0.9.14/CarlaUE4.sh`

The Carla binary step was not done. `just up` warns and skips Carla
startup; Autoware-only flows still work, but you can't drive without Carla.

### `Docker image missing: zenoh-carla-bridge-1.5.0`

The image build step was not done. `just setup` can't proceed.

### Carla starts but `port 2000 ... TIMEOUT`

Carla took >40 s to come up. Usually one of:

1. **DISPLAY hangs UE4** even with `-RenderOffScreen`. The script wraps
   Carla in `env -u DISPLAY`, so this only bites if you launched it yourself.
2. **GPU driver mismatch.** Carla 0.9.14 / UE4 4.26 wants a working Vulkan.
   RTX 50xx may need newer drivers.

## Known limits

- **Town01 only.** The mirror path
  `frontend/public/carla_map/Town01/lanelet2_map.osm` is hard-coded. Other
  Towns work in Carla, but you'd need to swap the download script and update
  `REACT_APP_MAP_FILE_PATH`.
- **Carla 0.9.14 only.** PythonAPI ABI shifted in 0.9.15+; the `carla`
  package pinned in `carla_agent`'s poetry venv is 0.9.14-specific.

These belong to the Carla integration, not the backend abstraction.
