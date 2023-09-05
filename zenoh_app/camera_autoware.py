# from zenoh_ros_type.common_interfaces.sensor_msgs import Image
import zenoh
import time
import sys
from flask import Flask, Response, request
from cv_bridge import CvBridge
import cv2
from werkzeug.serving import make_server

from dataclasses import dataclass
from pycdr2 import IdlStruct,Enum
from pycdr2.types import int8, uint8, int32, int64, uint32, uint64, float32, float64, sequence
@dataclass
class Time(IdlStruct, typename="Time"):
    sec: int32
    nanosec: uint32

@dataclass
class StdMsgsHeader(IdlStruct, typename="StdMsgsHeader"):
    stamp: Time
    frame_id: str

@dataclass
class Image(IdlStruct, typename="Image"):
    header: StdMsgsHeader
    height: uint32
    width: uint32
    encoding: str
    is_bigendian: uint8
    step: uint32
    data: sequence[uint8]


class MJPEG_server():
    def __init__(self, zenoh_session, scope):
        self.app = Flask(__name__)
        self.bridge = CvBridge()
        self.camera_image = None
        self.session = zenoh_session
        self.scope = scope
        self.host = None
        self.port = None
        self.server = None

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

        @self.app.route('/video')
        def video_feed():
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
        self.sub.undeclare()
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
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

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
        
if __name__ == "__main__":
    s = zenoh.open()
    server = MJPEG_server(s, 'v1')
    # import threading
    # t = threading.Thread(target=server.run)
    # t.start()
    # while True:
    #     c = input()
    #     if c == "s":
    #         server.shutdown()
    #         t.join()
    #     if c == "r":
    #         t = threading.Thread(target=server.run)
    #         t.start()