import threading

import numpy as np
import zenoh
from zenoh_ros_type.common_interfaces import Image

IMAGE_RAW_KEY_EXPR = '/sensing/camera/traffic_light/image_raw'

# At 20 FPS, 10 frames represent 0.5 second of video data
RING_CHANNEL_SIZE = 10


class MJPEG_server:
    def __init__(self, zenoh_session, scope, use_bridge_ros2dds=True):
        self.camera_image = None
        self.session = zenoh_session
        self.scope = scope
        self.use_bridge_ros2dds = use_bridge_ros2dds
        self.prefix = scope if use_bridge_ros2dds else scope + '/*'
        self.postfix = '' if use_bridge_ros2dds else '/**'
        self.height = None
        self.width = None
        self.processing = True

        self.sub_video = self.session.declare_subscriber(
            self.prefix + IMAGE_RAW_KEY_EXPR + self.postfix, zenoh.handlers.RingChannel(RING_CHANNEL_SIZE)
        )

        # Start processing thread
        self.frame_thread = threading.Thread(target=self.process_frame, daemon=True)
        self.frame_thread.start()

    def change_vehicle(self, new_scope):
        self.processing = False
        self.frame_thread.join()

        self.sub_video.undeclare()

        self.prefix = new_scope if self.use_bridge_ros2dds else new_scope + '/*'
        self.postfix = '' if self.use_bridge_ros2dds else '/**'
        self.sub_video = self.session.declare_subscriber(
            self.prefix + IMAGE_RAW_KEY_EXPR + self.postfix, zenoh.handlers.RingChannel(RING_CHANNEL_SIZE)
        )
        self.scope = new_scope

        self.width = None
        self.height = None

        self.processing = True
        self.frame_thread = threading.Thread(target=self.process_frame, daemon=True)
        self.frame_thread.start()

    def process_frame(self):
        while self.processing:
            try:
                if self.width is None or self.height is None:
                    sample = self.sub_video.try_recv()
                    if sample is None:
                        continue
                    image = Image.deserialize(sample.payload.to_bytes())
                    self.height = image.height
                    self.width = image.width

                sample = self.sub_video.try_recv()
                if sample is None:
                    continue

                data = sample.payload.to_bytes()

                # Each pixel is 4 bytes (RGBA), total bytes = Height x Width x 4.
                # Extract the last part of the ROS message as image data.
                np_image = np.frombuffer(data[-(self.height * self.width * 4) :], dtype=np.uint8)
                self.camera_image = np_image.reshape((self.height, self.width, 4))

            except Exception as e:
                print(f'Error processing frame: {e}')


if __name__ == '__main__':
    conf = zenoh.Config.from_file('config.json5')
    session = zenoh.open(conf)
    server = MJPEG_server(session, 'v1')
