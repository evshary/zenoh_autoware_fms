from zenoh_ros_type.tier4_autoware_msgs import CpuStatus, CpuUsage


def class2dict(instance):
    if not hasattr(instance, '__dict__'):
        return instance
    d = vars(instance)
    for key, value in d.items():
        if isinstance(value, list):
            d[key] = [class2dict(x) for x in value]
        else:
            d[key] = class2dict(value)
    return d


def parse_cpu_usage(cpu_raw):
    data = class2dict(CpuUsage.deserialize(cpu_raw))
    data['all']['status'] = CpuStatus.STATUS(data['all']['status']).name
    for cpu in data['cpus']:
        cpu['status'] = CpuStatus.STATUS(cpu['status']).name
    return data


def get_vehicle_status(telemetry):
    telemetry = telemetry or {}
    # turn_signal is not carried by the teleop telemetry; placeholder rather than
    # read Autoware directly.
    return {
        'status': {
            'twist': {'linear': {'x': telemetry.get('velocity', 0.0)}},
            'steering': {'data': telemetry.get('steer_angle', 0.0)},
            'turn_signal': {'data': 'NONE'},
            'gear_shift': {'data': telemetry.get('gear', 'NONE')},
        }
    }
