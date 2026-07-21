import struct
import threading
import time

import numpy as np
import zenoh
from zenoh_ros_type.common_interfaces import Image

# direct bridge key — deliberately no teleop relay
CAMERA_KEY_FMT = '{scope}/sensing/camera/traffic_light/image_raw'

# At 20 FPS, 10 frames represent 0.5 second of video data
RING_CHANNEL_SIZE = 10

IDLE_SLEEP = 0.02  # s


class MJPEG_server:
    def __init__(self, zenoh_session, scope):
        self.camera_image = None
        self.session = zenoh_session
        self.scope = scope
        self.height = None
        self.width = None
        self.processing = True

        self.sub_video = self.session.declare_subscriber(
            CAMERA_KEY_FMT.format(scope=scope), zenoh.handlers.RingChannel(RING_CHANNEL_SIZE)
        )
        self._last_warn = 0.0
        self.frame_thread = threading.Thread(target=self.process_frame, daemon=True)
        self.frame_thread.start()

    def process_frame(self):
        while self.processing:
            try:
                if self.width is None or self.height is None:
                    sample = self.sub_video.try_recv()
                    if sample is None:
                        time.sleep(IDLE_SLEEP)
                        continue
                    image = Image.deserialize(sample.payload.to_bytes())
                    self.height = image.height
                    self.width = image.width

                sample = self.sub_video.try_recv()
                if sample is None:
                    time.sleep(IDLE_SLEEP)
                    continue

                data = sample.payload.to_bytes()

                # RGBA pixels are the tail of the ROS message, past its header.
                np_image = np.frombuffer(data[-(self.height * self.width * 4) :], dtype=np.uint8)
                self.camera_image = np_image.reshape((self.height, self.width, 4))

            except (ValueError, TypeError, struct.error) as e:
                # Rate-limited: a persistently malformed stream arrives per frame.
                self.height = self.width = None  # re-probe dimensions
                if time.time() - self._last_warn > 5.0:
                    self._last_warn = time.time()
                    print(f'[MJPEG] dropping malformed frame for {self.scope}: {e}')
