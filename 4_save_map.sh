#!/bin/bash
# Luu ban do map.yaml va map.pgm
echo "=========================================================="
echo " [PHAN 2] Luu ban do map.yaml va map.pgm..."
echo "=========================================================="
source /home/hoangtam/.bashrc
source /opt/ros/humble/setup.bash

MAP_DIR="/home/hoangtam/ros2_ws/src/TurtleBot 4 Simulation/maps"
mkdir -p "$MAP_DIR"

ros2 run nav2_map_server map_saver_cli -f "$MAP_DIR/map" --ros-args -p map_subscribe_transient_local:=true -p use_sim_time:=true
echo ""
echo "Ban do da duoc luu thanh cong tai:"
ls -lh "$MAP_DIR"
