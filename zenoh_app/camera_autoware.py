from zenoh_ros_type.common_interfaces.sensor_msgs import Image
import zenoh
import time
import sys
from flask import Flask, Response
from cv_bridge import CvBridge
import cv2
import requests

class MJPEG_server():
    def __init__(self, zenoh_session, scope):
        self.app = Flask(__name__)
        self.bridge = CvBridge()
        self.camera_image = None
        self.session = zenoh_session
        self.scope = scope
        self.host = None
        self.port = None

        def callback(sample):
            data = Image.deserialize(sample.payload)
            self.camera_image = self.bridge.imgmsg_to_cv2(data, desired_encoding='passthrough')
        
        self.sub = self.session.declare_subscriber(
            f'{scope}/rt/sensing/camera/traffic_light/image_raw', 
            callback
        )

        @self.app.route('/')
        def index():
            return "Motion JPEG Server"

        @self.app.route("/shutdown", methods=["POST"])
        def shutdown():
            print(f"Shutting down motion jpeg server on vehicle {self.scope}...")
            request.environ.get("werkzeug.server.shutdown")()
            return "Shutting down..."

        @self.app.route('/video_feed')
        def video_feed():
            print('video_feed')
            return Response(
                self.generate_frame(), 
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
    
    def change_scope(self, new_scope):
        def callback(sample):
            data = Image.deserialize(sample.payload)
            self.camera_image = self.bridge.imgmsg_to_cv2(data, desired_encoding='passthrough')
        
        self.sub.undeclare()
        self.sub = self.session.declare_subscriber(
            f'{new_scope}/rt/sensing/camera/traffic_light/image_raw', 
            callback
        )
        self.scope = new_scope

    def shutdown(self):
        if self.host is not None and self.port is not None:
            requests.post(
                f"http://{self.host}:{self.port}/shutdown"
            )
            self.host = None
            self.port = None

    def generate_frame(self):
        while self.camera_image is None:
            pass
        while self.camera_image is not None:
            # Encode the frame as JPEG
            ret, buffer = cv2.imencode('.jpg', self.camera_image)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    def run(self, host='0.0.0.0', port=5000):
        if self.host is None and self.port is None:
            if host == '0.0.0.0':
                self.host = 'localhost'
            else:
                self.host = host
            
            self.port = port

            self.app.run(host=host, port=port)
        
if __name__ == "__main__":
    s = zenoh.open()
    server = MJPEG_server(s, 'v1')
    server.run()