#!/bin/bash
set -e

MAP_PATH="frontend/public/carla_map/Town01"

export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$MAP_PATH"
[ -f "$MAP_PATH/lanelet2_map.osm" ] || uvx gdown -O "$MAP_PATH/lanelet2_map.osm" 1vm9SvalJe7Bc9sh_8jK-0cPulVAov5uD
[ -f "$MAP_PATH/pointcloud_map.pcd" ] || uvx gdown -O "$MAP_PATH/pointcloud_map.pcd" 1MvJlfjkw3LWFUs5hdE_KQ2_CQTusU8UN
