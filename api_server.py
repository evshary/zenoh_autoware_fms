from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing_extensions import Annotated
from zenoh_app.list_autoware import list_autoware
from zenoh_app.status_autoware import *
from zenoh_app.teleop_autoware import *
from zenoh_app.camera_autoware import MJPEG_server
import zenoh
import math
import threading

MJPEG_HOST="0.0.0.0"
MJPEG_PORT=5000

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
)

conf = zenoh.Config.from_file('config.json5')
session = zenoh.open(conf)
manual_controller = None
mjpeg_server = None
mjpeg_server_thread = None

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/list")
async def manage_list_autoware():
    return list_autoware(session)

@app.get("/status/{scope}")
async def manage_status_autoware(scope):
    return {
        "cpu": get_cpu_status(session, scope),
        "vehicle": get_vehicle_status(session, scope)
    }

@app.get("/teleop/startup")
async def manage_teleop_startup(scope):
    global manual_controller, mjpeg_server, mjpeg_server_thread
    if manual_controller is not None:
        manual_controller.stop_teleop()
    manual_controller = ManualController(session, scope)

    if mjpeg_server is not None:
        mjpeg_server.change_scope(scope)
    else:
        mjpeg_server = MJPEG_server(session, scope)
        mjpeg_server_thread = threading.Thread(target = mjpeg_server.run)
        mjpeg_server_thread.start()
    return {
        "text": f"Startup manual control on {scope}.",
        "mjpeg_host": "localhost" if MJPEG_HOST == "0.0.0.0" else MJPEG_HOST,
        "mjpeg_port": MJPEG_PORT
    }

@app.get("/teleop/gear")
async def manage_teleop_gear(scope, gear):
    global manual_controller
    if manual_controller is not None:
        manual_controller.pub_gear(gear)
        return f"Set gear {gear} to {scope}."
    else:
        return "Please startup the teleop first"

@app.get("/teleop/velocity")
async def manage_teleop_speed(scope, velocity):
    global manual_controller
    if manual_controller is not None:
        manual_controller.update_control_command(float(velocity) * 1000 / 3600, None)
        return f"Set speed {velocity} to {scope}."
    else:
        return "Please startup the teleop first"

@app.get("/teleop/turn")
async def manage_teleop_turn(scope, angle):
    global manual_controller
    if manual_controller is not None:
        manual_controller.update_control_command(None, float(angle) * math.pi / 180)
        return f"Set steering angle {angle}."
    else:
        return "Please startup the teleop first"


@app.get("/teleop/status")
async def manage_teleop_status():
    global manual_controller
    if manual_controller is not None:
        return {
            'velocity': manual_controller.current_velocity,
            'gear': manual_controller.current_gear,
            'steering': manual_controller.current_steer * 180 / math.pi
        }
    else:
        return {
            'velocity': '---',
            'gear': '---',
            'steering': '---'
        }