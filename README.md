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

