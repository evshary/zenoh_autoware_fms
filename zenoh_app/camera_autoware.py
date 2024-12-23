import queue
import threading

import cv2
import zenoh
from cv_bridge import CvBridge
from flask import Flask, Response
from werkzeug.serving import make_server
from zenoh_ros_type.common_interfaces import Image
from zenoh_ros_type.rcl_interfaces import Clock

IMAGE_RAW_KEY_EXPR = '/sensing/camera/traffic_light/image_raw'
CLOCK_KEY_EXPR = '/clock'

MAX_FRAME_DELAY = 0.5

class MJPEG_server:
    def __init__(self, zenoh_session, scope, use_bridge_ros2dds=True):
        self.app = Flask(__name__)
        self.bridge = CvBridge()
        self.camera_image = None
        self.clock = None
        self.session = zenoh_session
        self.scope = scope
        self.host = None
        self.port = None
        self.server = None
        self.use_bridge_ros2dds = use_bridge_ros2dds
        self.prefix = scope if use_bridge_ros2dds else scope + '/rt'
        
        # Queue for threading
        self.frame_queue = queue.Queue()
        
        # Start processing thread
        self.frame_thread = threading.Thread(target=self.process_frame, daemon=True)
        self.frame_thread.start()

        def callback(sample):
            self.frame_queue.put(sample)

        def callback_clock(sample):
            clock_data = Clock.deserialize(sample.payload.to_bytes())
            self.clock = clock_data.clock.sec + clock_data.clock.nanosec * 1e-9

        self.sub_video = self.session.declare_subscriber(self.prefix + IMAGE_RAW_KEY_EXPR, callback)
        self.sub_clock = self.session.declare_subscriber(self.prefix + CLOCK_KEY_EXPR, callback_clock)

        @self.app.route('/')
        def index():
            return 'Motion JPEG Server'

        @self.app.route('/video')
        def video_feed():
            return Response(self.generate_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')

    def change_scope(self, new_scope):
        def callback(sample):
            self.frame_queue.put(sample)

        def callback_clock(sample):
            clock_data = Clock.deserialize(sample.payload.to_bytes())
            self.clock = clock_data.clock.sec + clock_data.clock.nanosec * 1e-9

        self.frame_queue.queue.clear()
        self.sub_video.undeclare()
        self.sub_clock.undeclare()
        self.prefix = new_scope if self.use_bridge_ros2dds else new_scope + '/rt'
        self.sub_video = self.session.declare_subscriber(self.prefix + IMAGE_RAW_KEY_EXPR, callback)
        self.sub_clock = self.session.declare_subscriber(self.prefix + CLOCK_KEY_EXPR, callback_clock)
        self.scope = new_scope
        
    def process_frame(self):
        while True:
            sample = self.frame_queue.get()
            try:
                if sample is None or self.clock is None:
                    continue
                
                data = Image.deserialize(sample.payload.to_bytes())
                camera_image_time = data.header.stamp.sec + data.header.stamp.nanosec * 1e-9
                
                if self.clock - camera_image_time > MAX_FRAME_DELAY:
                    continue
                
                self.camera_image = self.bridge.imgmsg_to_cv2(data, desired_encoding='passthrough')
            except Exception as e:
                print(f"Error processing frame: {e}")

    def shutdown(self):
        self.sub_video.undeclare()
        self.sub_clock.undeclare()
        self.frame_queue.put(None)
        self.frame_thread.join()
        
        if self.host is not None and self.port is not None:
            self.server.shutdown()
            self.server = None
            self.host = None
            self.port = None

    def generate_frame(self):
        while self.camera_image is None:
            pass
        while self.camera_image is not None:
            # Encode the frame as JPEG
            ret, buffer = cv2.imencode('.jpg', self.camera_image)
            frame = buffer.tobytes()
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n' b'Cache-Control: no-cache\r\n\r\n' + frame + b'\r\n')

    def run(self, host='0.0.0.0', port=5000):
        if self.host is None and self.port is None:
            if host == '0.0.0.0':
                self.host = 'localhost'
            else:
                self.host = host

            self.port = port

            # self.app.run(host=host, port=port)
            self.server = make_server(host, port, self.app)
            self.server.serve_forever()


if __name__ == '__main__':
    s = zenoh.open()
    server = MJPEG_server(s, 'v1')