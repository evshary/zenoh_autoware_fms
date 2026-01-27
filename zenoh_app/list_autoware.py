import json


def list_autoware(session, use_bridge_ros2dds=True, search_times=10):
    ### uuid --> scope, address
    agent_infos = {}

    ### Retrive scope from admin space of zenoh-bridge-dds
    for _ in range(search_times):
        if use_bridge_ros2dds:
            replies = session.get('@/**/ros2/config')
        else:
            replies = session.get('@/**/config/**')
        for reply in replies:
            try:
                key_expr_ = str(reply.ok.key_expr)
                payload_ = json.loads(reply.ok.payload.to_string())

                if use_bridge_ros2dds:
                    uuid = key_expr_.split('/')[1].lower()
                    # Need to remove /
                    scope = payload_['namespace'][1:]
                else:
                    uuid = payload_['routers'][0]
                    scope = key_expr_.split('/')[4].lower()

                if uuid not in agent_infos.keys():
                    agent_infos[uuid] = {}
                agent_infos[uuid]['scope'] = scope
            except Exception as _e:
                pass

        ### Retrive ip from admin space of zenoh-bridge-dds
        replies = session.get('@/**/session/**/link/**')
        for reply in replies:
            try:
                key_expr_ = str(reply.ok.key_expr)
                payload_ = json.loads(reply.ok.payload.to_string())

                uuid = key_expr_.split('/')[5].lower()
                address = payload_['dst']

                if uuid in agent_infos.keys():
                    agent_infos[uuid]['address'] = address
            except Exception as _e:
                pass

    return list(agent_infos.values())
