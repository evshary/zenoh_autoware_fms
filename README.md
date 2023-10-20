# zenoh_autoware_fms

The project is the FMS (fleet management system) prototype of Autoware based on Zenoh.

# Usage

* Install prerequisite

```shell
./prerequisite.sh
```

* Run Web Server & API Server

```shell
# Source ROS 2 environment
./run_server.sh
```

* You can use environment [here](https://github.com/evshary/zenoh_demo_docker_env/tree/main/autoware_multiple_fms) to test FMS
    - Remember to change the IP in `docker-compose.yml` to FMS IP.

# Development

* API Server: http://127.0.0.1:8000/docs

# Project

Please check our roadmap in [GitHub Project](https://github.com/users/evshary/projects/2)
