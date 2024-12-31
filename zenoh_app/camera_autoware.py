import threading

import numpy as np
import zenoh
from zenoh_ros_type.common_interfaces import CameraInfo

IMAGE_RAW_KEY_EXPR = '/sensing/camera/traffic_light/image_raw'
CAMERA_INFO_KEY_EXPR = '/sensing/camera/traffic_light/camera_info'

# At 20 FPS, 10 frames represent 0.5 second of video data
RING_CHANNEL_SIZE = 10


class MJPEG_server:
    def __init__(self, zenoh_session, scope, use_bridge_ros2dds=True):
        self.camera_image = None
        self.session = zenoh_session
        self.scope = scope
        self.use_bridge_ros2dds = use_bridge_ros2dds
        self.prefix = scope if use_bridge_ros2dds else scope + '/rt'
        self.height = None
        self.width = None

        self.sub_info = self.session.declare_subscriber(self.prefix + CAMERA_INFO_KEY_EXPR)
        self.sub_video = self.session.declare_subscriber(self.prefix + IMAGE_RAW_KEY_EXPR, zenoh.handlers.RingChannel(RING_CHANNEL_SIZE))

        # Start processing thread
        self.frame_thread = threading.Thread(target=self.process_frame, daemon=True)
        self.frame_thread.start()

    def change_scope(self, new_scope):
        self.sub_info.undeclare()
        self.sub_video.undeclare()

        self.prefix = new_scope if self.use_bridge_ros2dds else new_scope + '/rt'
        self.sub_info = self.session.declare_subscriber(self.prefix + CAMERA_INFO_KEY_EXPR)
        self.sub_video = self.session.declare_subscriber(self.prefix + IMAGE_RAW_KEY_EXPR, zenoh.handlers.RingChannel(RING_CHANNEL_SIZE))
        self.scope = new_scope

        self.width = None
        self.height = None

    def process_frame(self):
        while True:
            try:
                if self.width is None or self.height is None:
                    sample = self.sub_video.try_recv()
                    if sample is None:
                        continue
                    camera_info = CameraInfo.deserialize(sample.payload.to_bytes())
                    self.height = camera_info.height
                    self.width = camera_info.width

                sample = self.sub_video.try_recv()
                if sample is None:
                    continue

                data = sample.payload.to_bytes()
                np_data = np.frombuffer(data[-(self.height * self.width * 4) :], dtype=np.uint8)
                self.camera_image = np_data.reshape((self.height, self.width, 4))

            except Exception as e:
                print(f'Error processing frame: {e}')


if __name__ == '__main__':
    s = zenoh.open()
    server = MJPEG_server(s, 'v1')
