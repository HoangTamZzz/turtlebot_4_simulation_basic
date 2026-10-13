#!/bin/bash
# Dieu khien thu cong TurtleBot 4 bang ban phim
echo "=========================================================="
echo " [TELEOP] Khoi dong bo dieu khien TurtleBot 4 bang ban phim"
echo "=========================================================="
source /home/hoangtam/.bashrc
source /opt/ros/humble/setup.bash

SCRIPT_DIR="/home/hoangtam/ros2_ws/src/TurtleBot 4 Simulation/scripts"
python3 "$SCRIPT_DIR/teleop_keyboard.py" --ros-args -p use_sim_time:=true
