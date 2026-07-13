import asyncio
import json

import cv2
import zenoh
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from zenoh_app.camera_autoware import MJPEG_server
from zenoh_app.fleet_manager import FleetManager, InvalidScope, validate_scope
from zenoh_app.list_autoware import BridgeTracker, TeleopTracker
from zenoh_app.pose_service import PoseServer
from zenoh_app.status_autoware import get_vehicle_status, parse_cpu_usage

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

conf = zenoh.Config.from_file('config.json5')
session = zenoh.open(conf)


def _checked_scope(scope):
    # Operator-supplied scope flows into zenoh keys, filenames and YAML, so
    # reject anything but a tame token before it reaches any of them.
    try:
        return validate_scope(scope)
    except InvalidScope as e:
        raise HTTPException(status_code=400, detail=str(e))


async def _ws_scope(websocket, scope):
    # WS twin of _checked_scope: policy-close instead of an HTTP 400.
    try:
        return validate_scope(scope)
    except InvalidScope:
        await websocket.close(code=1008)
        return None


class Scope:
    """Per-scope server channels: intent pub, telemetry sub + cache, camera."""
    def __init__(self, name, session):
        self.last_telemetry = {}
        self.last_cpu = None
        self.intent_pub = session.declare_publisher(f'manual_control/{name}/intent')
        self.telemetry_sub = session.declare_subscriber(
            f'manual_control/{name}/telemetry', self._on_telemetry)
        self.cpu_sub = session.declare_subscriber(
            f'{name}/api/external/get/cpu_usage', self._on_cpu)
        # lazy: an attached-but-unwatched scope spins no decode thread
        self._session = session
        self._name = name
        self._mjpeg = None

    @property
    def mjpeg(self):
        if self._mjpeg is None:
            self._mjpeg = MJPEG_server(self._session, self._name)
        return self._mjpeg

    def _on_telemetry(self, sample):
        try:
            self.last_telemetry = json.loads(sample.payload.to_bytes().decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f'[API SERVER] dropping malformed telemetry sample: {e}')

    def _on_cpu(self, sample):
        # parse at receipt: one bad sample must not 500 /status
        try:
            self.last_cpu = parse_cpu_usage(sample.payload.to_bytes())
        except Exception as e:
            print(f'[API SERVER] dropping malformed cpu sample: {e}')


class ScopeRegistry:
    def __init__(self, session):
        self._session = session
        self._scopes = {}

    def get(self, name):
        if name not in self._scopes:
            self._scopes[name] = Scope(name, self._session)
        return self._scopes[name]


scopes = ScopeRegistry(session)
teleop_tracker = TeleopTracker(session)
bridge_tracker = BridgeTracker(session)
fleet = FleetManager(bridge_tracker)
pose_service = PoseServer(session, bridge_tracker)


@app.on_event('startup')
async def _start_fleet_supervision():
    fleet.start()


@app.on_event('shutdown')
async def _stop_fleet_supervision():
    # Off the loop: stopping teleops blocks up to their term grace.
    await asyncio.to_thread(fleet.shutdown)


@app.get('/')
async def root():
    return {'message': 'Hello World'}


@app.get('/list')
async def manage_list_autoware():
    # held (FMS owns a teleop) stays listed with presence dropped, so the zombie is detachable
    attached = {v['scope'] for v in teleop_tracker.list()}
    discovered = set(bridge_tracker.list())
    held = set(fleet.held_scopes())
    return [
        {'scope': s,
         'state': 'ATTACHED' if s in attached else 'DISCOVERED',
         'held': s in held,
         'teleop': fleet.status(s),
         'address': f'teleop:{s}' if s in attached else f'bridge:{s}'}
        for s in sorted(attached | discovered | held)
    ]


# plain def = FastAPI threadpool: blocking attach/map IO must not stall the loop
# (frozen WS = frozen deadman intent)
@app.post('/fleet/attach')
def fleet_attach(scope: str):
    return fleet.attach(_checked_scope(scope))


@app.post('/fleet/detach')
def fleet_detach(scope: str):
    return fleet.detach(_checked_scope(scope))


@app.get('/zenoh/has-subscriber')
async def zenoh_has_subscriber(key: str):
    pub = session.declare_publisher(key)
    try:
        return {'matching': bool(pub.matching_status.matching)}
    finally:
        pub.undeclare()


@app.get('/status/{scope}')
async def manage_status_autoware(scope: str):
    sc = scopes.get(_checked_scope(scope))
    return {'cpu': sc.last_cpu, 'vehicle': get_vehicle_status(sc.last_telemetry)}


@app.websocket('/video')
async def handle_ws(websocket: WebSocket, scope: str = 'v1'):
    await websocket.accept()
    scope = await _ws_scope(websocket, scope)
    if scope is None:
        return
    mjpeg = scopes.get(scope).mjpeg
    try:
        while True:
            if mjpeg.camera_image is None:
                await asyncio.sleep(2)
            else:
                _, buffer = cv2.imencode('.jpg', mjpeg.camera_image)
                await websocket.send_bytes(buffer.tobytes())
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass


@app.websocket('/telemetry/stream')
async def telemetry_stream(websocket: WebSocket, scope: str = 'v1'):
    await websocket.accept()
    scope = await _ws_scope(websocket, scope)
    if scope is None:
        return
    s = scopes.get(scope)
    try:
        while True:
            await websocket.send_json(s.last_telemetry)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass


@app.get('/teleop/startup')
def manage_teleop_startup(scope: str = 'v1'):
    scope = _checked_scope(scope)
    status = fleet.attach(scope)
    scopes.get(scope)  # prime channels (side effect)
    return status


@app.websocket('/teleop/intent/ws')
async def handle_intent_ws(websocket: WebSocket, scope: str = 'v1'):
    await websocket.accept()
    scope = await _ws_scope(websocket, scope)
    if scope is None:
        return
    intent_pub = scopes.get(scope).intent_pub
    try:
        while True:
            data = await websocket.receive_text()
            intent_pub.put(data)
    except WebSocketDisconnect:
        pass


@app.get('/map/list')
def get_vehicle_list():
    pose_service.findVehicles()
    return list(pose_service.vehicles.keys())


@app.get('/map/pose')
def get_vehicle_pose():
    return pose_service.returnPose()


@app.get('/map/goalPose')
def get_vehicle_goalpose():
    return pose_service.returnGoalPose()


@app.get('/map/setGoal')
def set_goal_pose(scope: str, lat: float, lon: float):
    scope = _checked_scope(scope)
    if scope not in pose_service.vehicles:
        raise HTTPException(status_code=404, detail=f'unknown scope: {scope}')
    print(f'[API SERVER] Set Goal Pose of {scope} as (lat={lat}, lon={lon})')
    pose_service.setGoal(scope, lat, lon)
    return 'success'


@app.get('/map/engage')
def set_engage(scope: str):
    scope = _checked_scope(scope)
    if scope not in pose_service.vehicles:
        raise HTTPException(status_code=404, detail=f'unknown scope: {scope}')
    pose_service.engage(scope)
    return 'success'
