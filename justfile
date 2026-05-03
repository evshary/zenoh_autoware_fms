run_rmw_zenoh:
    USE_BRIDGE_ROS2DDS=False just run

run_ros2dds:
    USE_BRIDGE_ROS2DDS=True just run

run:
    #!/usr/bin/env bash
    source env.sh
    echo "API:      http://localhost:8000"
    echo "Frontend: http://localhost:3000"
    # `env -u PYTHONPATH`: prevent ROS-sourced shells from leaking system-Python
    # site-packages into uv's venv (lanelet2 ABI-incompatible build crashes import).
    # `--host 0.0.0.0`: reachable across Docker / SSH-forward boundaries; superset
    # of the previous default 127.0.0.1.
    parallel --verbose --lb ::: \
        'env -u PYTHONPATH uv run uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload 2>&1 | tee logs/api_server.log' \
        'cd frontend && npm start 2>&1 | tee logs/frontend.log'

clean:
    rm -rf __pycache__ .venv
 