import asyncio
import json
import os

import cv2
import zenoh
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from zenoh_app.camera_autoware import MJPEG_server
from zenoh_app.list_autoware import list_autoware
from zenoh_app.pose_service import PoseServer
from zenoh_app.status_autoware import get_cpu_status, get_vehicle_status
from zenoh_app.teleop_autoware import ManualController

MJPEG_HOST = '0.0.0.0'
MJPEG_PORT = 5000

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

conf = zenoh.Config.from_file('config.json5')
session = zenoh.open(conf)
use_bridge_ros2dds = os.environ.get('USE_BRIDGE_ROS2DDS') == 'True'
mjpeg_server = None
pose_service = PoseServer(session, use_bridge_ros2dds)

# ── Zenoh intent publisher (browser → remote_control via Zenoh) ──
_intent_pub = session.declare_publisher('manual_control/intent')

# ── Zenoh telemetry subscriber (remote_control → browser via Zenoh) ──
_last_telemetry = {}

def _on_telemetry(sample):
    global _last_telemetry
    try:
        _last_telemetry = json.loads(sample.payload.to_bytes().decode('utf-8'))
    except Exception:
        pass

_telemetry_sub = session.declare_subscriber('manual_control/telemetry', _on_telemetry)


@app.get('/')
async def root():
    return {'message': 'Hello World'}


@app.get('/list')
async def manage_list_autoware():
    return list_autoware(session, use_bridge_ros2dds)


@app.get('/zenoh/has-subscriber')
async def zenoh_has_subscriber(key: str):
    # Probes the Zenoh routing graph for any subscriber matching `key`.
    # Used by the frontend to detect bridge-side capabilities (e.g. whether
    # zenoh_carla_bridge was built with the `initialpose` cargo feature) —
    # subscription presence IS the capability, no extra contract needed.
    pub = session.declare_publisher(key)
    try:
        return {'matching': bool(pub.matching_status.matching)}
    finally:
        pub.undeclare()


@app.get('/status/{scope}')
async def manage_status_autoware(scope):
    return {'cpu': get_cpu_status(session, scope, use_bridge_ros2dds), 'vehicle': get_vehicle_status(session, scope, use_bridge_ros2dds)}


@app.websocket('/video')
async def handle_ws(websocket: WebSocket):
    await websocket.accept()
    global mjpeg_server
    try:
        while True:
            if mjpeg_server is None or mjpeg_server.camera_image is None:
                await asyncio.sleep(1)
            else:
                _, buffer = cv2.imencode('.jpg', mjpeg_server.camera_image)
                await websocket.send_bytes(buffer.tobytes())
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass


@app.websocket('/telemetry/stream')
async def telemetry_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(_last_telemetry)
            await asyncio.sleep(0.1)  # 10Hz
    except WebSocketDisconnect:
        pass


@app.get('/teleop/startup')
async def manage_teleop_startup(scope: str = 'v1'):
    """Initialize gate mode + camera. Control goes through Zenoh intent to remote_control."""
    global mjpeg_server
    # ManualController only sets EXTERNAL gate mode + change_to_remote;
    # the C++ remote_control node owns the live control loop.
    mc = ManualController(session, scope, use_bridge_ros2dds)
    mc.stop_teleop()

    if mjpeg_server is not None:
        mjpeg_server.change_vehicle(scope)
    else:
        mjpeg_server = MJPEG_server(session, scope, use_bridge_ros2dds)
    return {
        'text': f'Startup teleop on {scope}. Control via Zenoh intent.',
        'mjpeg_host': 'localhost' if MJPEG_HOST == '0.0.0.0' else MJPEG_HOST,
        'mjpeg_port': MJPEG_PORT,
    }


# ── WebSocket: browser intent → Zenoh (manual_control/intent) ──

@app.websocket('/teleop/intent/ws')
async def handle_intent_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            _intent_pub.put(data)
    except WebSocketDisconnect:
        # Safety: send reset intent so watchdog triggers safe stop
        try:
            reset = {'w': False, 's': False, 'a': False, 'd': False, 'space': False, 'client_id': ''}
            _intent_pub.put(json.dumps(reset))
        except Exception:
            pass


@app.get('/map/list')
async def get_vehilcle_list():
    global pose_service
    pose_service.findVehicles()
    return list(pose_service.vehicles.keys())


@app.get('/map/pose')
async def get_vehicle_pose():
    global pose_service
    if pose_service is not None:
        return pose_service.returnPose()
    else:
        return []


@app.get('/map/goalPose')
async def get_vehicle_goalpose():
    global pose_service
    if pose_service is not None:
        return pose_service.returnGoalPose()
    else:
        return []


@app.get('/map/setGoal')
async def set_goal_pose(scope, lat, lon):
    global pose_service
    if pose_service is not None:
        print(f'[API SERVER] Set Goal Pose of {scope} as (lat={lat}, lon={lon})')
        pose_service.setGoal(scope, lat, lon)
        return 'success'
    else:
        return 'fail'


@app.get('/map/engage')
async def set_engage(scope):
    global pose_service
    if pose_service is not None:
        pose_service.engage(scope)
        return 'success'
    else:
        return 'fail'
