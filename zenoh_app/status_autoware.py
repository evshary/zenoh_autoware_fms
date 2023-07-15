import zenoh
import json
import time
import sys
from .structure import *
from pycdr2 import Dict

def class2dict(instance, built_dict={}):
    ### Reference: https://stackoverflow.com/questions/63893843/how-to-convert-nested-object-to-nested-dictionary-in-python
    if not hasattr(instance, "__dict__"):
        return instance
    new_subdic = vars(instance)
    for key, value in new_subdic.items():
        if isinstance(new_subdic[key], list):
            for i in range(len(new_subdic[key])):
                new_subdic[key][i] = class2dict(new_subdic[key][i])
        else:
            new_subdic[key] = class2dict(value)
    return new_subdic

def get_cpu_status(session, scope):
    cpu_key_expr = f'{scope}/rt/api/external/get/cpu_usage'
    print(cpu_key_expr)
    sub = session.declare_subscriber(cpu_key_expr, zenoh.Queue(), reliability=zenoh.Reliability.RELIABLE())
    cpu_status_data = None
    while cpu_status_data is None:
        time.sleep(1)
        for rep in sub.receiver:
            cpu_status_data = cpu_usage.deserialize(rep.payload)
            break
    ### Convert object to dictionary
    cpu_status_data = class2dict(cpu_status_data)
    cpu_status_data['all']['status'] = CpuStatus.STATUS(cpu_status_data['all']['status']).name
    for i in range(len(cpu_status_data['cpus'])):
        cpu_status_data['cpus'][i]['status'] = CpuStatus.STATUS(cpu_status_data['cpus'][i]['status']).name
    print(cpu_status_data)
    return cpu_status_data

def get_vehicle_status(session, scope):
    vehicle_status_key_expr = f'{scope}/rt/api/external/get/vehicle/status'
    print(vehicle_status_key_expr)
    sub = session.declare_subscriber(vehicle_status_key_expr, zenoh.Queue(), reliability=zenoh.Reliability.RELIABLE())
    vehicle_status_data = None
    while vehicle_status_data is None:
        time.sleep(1)
        for rep in sub.receiver:
            vehicle_status_data = vehicle_status.deserialize(rep.payload)
            break
    ### Convert object to dictionary
    vehicle_status_data = class2dict(vehicle_status_data)
    vehicle_status_data['status']['gear_shift']['data'] = GearShift.GEAR(vehicle_status_data['status']['gear_shift']['data']).name
    vehicle_status_data['status']['turn_signal']['data'] = TurnSignal.TURN(vehicle_status_data['status']['turn_signal']['data']).name
    print(vehicle_status_data)
    return vehicle_status_data

if __name__ == "__main__":
    conf = zenoh.Config()
    conf.insert_json5(zenoh.config.LISTEN_KEY, json.dumps(['tcp/172.17.0.1:7447']))
    s = zenoh.open(conf)
    get_cpu_status(s, 'v1')
    get_vehicle_status(s, 'v1')



