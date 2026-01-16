import time

import zenoh
from zenoh_ros_type.tier4_autoware_msgs import CpuStatus, CpuUsage, GearShift, TurnSignal, VehicleStatusStamped

GET_CPU_KEY_EXPR = '/api/external/get/cpu_usage'
GET_VEHICLE_STATUS_KEY_EXPR = '/api/external/get/vehicle/status'


def class2dict(instance, built_dict={}):
    ### Reference: https://stackoverflow.com/questions/63893843/how-to-convert-nested-object-to-nested-dictionary-in-python
    if not hasattr(instance, '__dict__'):
        return instance
    new_subdic = vars(instance)
    for key, value in new_subdic.items():
        if isinstance(new_subdic[key], list):
            for i in range(len(new_subdic[key])):
                new_subdic[key][i] = class2dict(new_subdic[key][i])
        else:
            new_subdic[key] = class2dict(value)
    return new_subdic


def get_cpu_status(session, scope, use_bridge_ros2dds=True):
    prefix = scope if use_bridge_ros2dds else scope + '/*'
    postfix = '' if use_bridge_ros2dds else '/**'
    cpu_key_expr = prefix + GET_CPU_KEY_EXPR + postfix
    print(cpu_key_expr, flush=True)
    sub = session.declare_subscriber(cpu_key_expr)
    cpu_status_data = None
    while cpu_status_data is None:
        time.sleep(1)
        for rep in sub:
            cpu_status_data = CpuUsage.deserialize(rep.payload.to_bytes())
            break
    ### Convert object to dictionary
    cpu_status_data = class2dict(cpu_status_data)
    cpu_status_data['all']['status'] = CpuStatus.STATUS(cpu_status_data['all']['status']).name
    for i in range(len(cpu_status_data['cpus'])):
        cpu_status_data['cpus'][i]['status'] = CpuStatus.STATUS(cpu_status_data['cpus'][i]['status']).name
    print(cpu_status_data)
    return cpu_status_data


def get_vehicle_status(session, scope, use_bridge_ros2dds=True):
    prefix = scope if use_bridge_ros2dds else scope + '/*'
    postfix = '' if use_bridge_ros2dds else '/**'
    vehicle_status_key_expr = prefix + GET_VEHICLE_STATUS_KEY_EXPR + postfix
    print(vehicle_status_key_expr, flush=True)
    sub = session.declare_subscriber(vehicle_status_key_expr)
    vehicle_status_data = None
    while vehicle_status_data is None:
        time.sleep(1)
        for rep in sub:
            vehicle_status_data = VehicleStatusStamped.deserialize(rep.payload.to_bytes())
            break
    ### Convert object to dictionary
    vehicle_status_data = class2dict(vehicle_status_data)
    vehicle_status_data['status']['gear_shift']['data'] = GearShift.DATA(vehicle_status_data['status']['gear_shift']['data']).name
    vehicle_status_data['status']['turn_signal']['data'] = TurnSignal.DATA(vehicle_status_data['status']['turn_signal']['data']).name
    print(vehicle_status_data)
    return vehicle_status_data


if __name__ == '__main__':
    conf = zenoh.Config.from_file('config.json5')
    session = zenoh.open(conf)
    get_cpu_status(session, 'v1')
    get_vehicle_status(session, 'v1')
