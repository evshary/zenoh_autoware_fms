run_rmw_zenoh:
    USE_BRIDGE_ROS2DDS=False just run

run_ros2dds:
    USE_BRIDGE_ROS2DDS=True just run

run:
    echo "Connect to http://127.0.0.1:8080"
    parallel --verbose --lb ::: \
        'uv run uvicorn api_server:app --reload 2>&1 | tee logs/api_server.log' \
        'cd frontend && npm start | tee logs/frontend.log'

clean:
    rm -rf __pycache__ .venv
 