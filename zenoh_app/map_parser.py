from lanelet2.projection import UtmProjector
from lanelet2.io import Origin
from lanelet2.core import BasicPoint3d, GPSPoint
import lanelet2

import math

import numpy as np

def proj_between(p1, p2, p3):
    ### A segment p1 to p2
    ### Project p3 to segment p1 p2, check whether it is between p1 and p2
    # projLen = np.dot((p3-p1), (p2-p1)) / (np.linalg.norm(p2-p1) * np.linalg.norm(p2-p1))
    # p = p1 + projLen * (p2-p1)
    return (np.dot((p3-p1), (p3-p2)) <  0)

def point2line(p1, p2, p3):
    d = np.cross(p2-p1,p3-p1)/np.linalg.norm(p2-p1)
    return d * d

def vec2degree(v1, v2):
    dx = v2.x - v1.x
    dy = v2.y - v1.y
    angle = math.atan(dy / dx)
    if dx < 0: ## II or III quadrant
      angle += math.pi
    return angle
    

class OrientationParser:
    def __init__(self, path='frontend/public/carla_map/Town01/lanelet2_map.osm', originX=0, originY=0):
        self.mapPath = path
        self.proj = UtmProjector(Origin(originX, originY))
        self.vmap = lanelet2.io.load(path, self.proj)
        self.points = {}
        self.ways = {}
        self.initialize()

    def initialize(self):
        for p in self.vmap.pointLayer:
            self.points[p.id] = p

        for line in self.vmap.lineStringLayer:
            self.ways[line.id] = [point for point in line]

    def genQuaternion_seg(self, x, y):
        ### 1. Find the segment(line) nearest with (x, y)
        min_dis = 2147483647
        min_dis_id = -1
        min_dis_yaw = 0

        for lineID, way in self.ways.items():
            for from_, to_ in zip(way, way[1:]):
                p1 = np.array([from_.x, from_.y])
                p2 = np.array([to_.x, to_.y])
                p3 = np.array([x, y])
                if proj_between(p1, p2, p3):
                    dis = point2line(p1, p2, p3)
                    if dis < min_dis:
                        print(lineID, dis)
                        min_dis_id = lineID
                        min_dis = dis
                        min_dis_yaw = vec2degree(from_, to_)
        print(min_dis_id)
        return [0, 0, math.sin(min_dis_yaw/2), math.cos(min_dis_yaw/2)]

if __name__ == "__main__":
    op = OrientationParser('lanelet2_map.osm', originX=35.23808753540768, originY=139.9009591876285)
    op = OrientationParser('Town01.osm', originX=0, originY=0)
    # x = float(input('x: '))
    # y = float(input('y: '))
    
    print(op.genQuaternion_seg(
        318.74114990234375, 
        -134.72076416015625
    ))
    # op.plotLane(114.7998046875, -200.10482788085938)