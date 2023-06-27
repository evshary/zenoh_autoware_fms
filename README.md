# zenoh_autoware_fms

The project is the FMS (fleet management system) prototype of Autoware based on Zenoh.

# Usage

* Prerequisite

```shell
# Install poetry
curl -sSL https://install.python-poetry.org | python3 -
poetry config virtualenvs.in-project true

# Install packages
sudo apt install parallel
# Install Python packages
poetry install
```

* Run Web Server & API Server

```shell
./run_server.sh
```

* You can use environment [here](https://github.com/evshary/zenoh_demo_docker_env/tree/main/autoware_multiple_fms) to test FMS

# Roadmap

Here are some functions we'll implement in the future:

* Use docker-compose to run multiple Autoware (planning simulator) with zenoh-bridge-dds at the same time.
* List all available Autoware
* Get the basic information from any Autoware (Use AD API)
  - `/api/external/get/cpu_usage`
  - `/api/external/get/vehicle/status`
* Assign goal to Autoware (Use [AD API](https://autowarefoundation.github.io/autoware-documentation/main/design/autoware-interfaces/ad-api/use-cases/drive-designated-position/))
* Manage multiple vehicles in the same Carla simulator
* Show the camera image from any Autoware
* Remote teleop vehicle in any Autoware
* Support Autoware in ROS 1 with the help of [zenoh-plugin-ros1](https://github.com/eclipse-zenoh/zenoh-plugin-ros1)

