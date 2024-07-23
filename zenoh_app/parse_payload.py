from zenoh_ros_type.autoware_adapi_msgs import ChangeOperationMode, ResponseStatus


def ChangeOperationMode_payload(payload: bytes) -> ChangeOperationMode:
    success_payload = payload[1]
    code_payload = payload[6:8]

    success = success_payload == 1
    code = int.from_bytes(code_payload, byteorder='little')
    message = payload[12:].decode('utf-8').strip('\x00')

    status = ResponseStatus(success=success, code=code, message=message)
    return ChangeOperationMode(status=status)