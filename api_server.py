from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from zenoh_app.list_autoware import list_autoware
from zenoh_app.status_autoware import *
import zenoh

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
)

conf = zenoh.Config.from_file('config.json5')
session = zenoh.open(conf)

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