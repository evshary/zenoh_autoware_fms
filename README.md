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

# Development

* API Server: http://127.0.0.1:8000/docs

# Project

Please check our roadmap in [GitHub Project](https://github.com/users/evshary/projects/2)
