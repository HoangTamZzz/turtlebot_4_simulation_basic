#!/bin/bash
# Tu dong lai robot di kham pha me cung de quet ban do sach dep
echo "=========================================================="
echo " [AUTO EXPLORE] Robot tu dong lai de quet ban do..."
echo "=========================================================="
source /home/hoangtam/.bashrc
source /opt/ros/humble/setup.bash

python3 "/home/hoangtam/ros2_ws/src/TurtleBot 4 Simulation/scripts/auto_explorer.py" --ros-args -p use_sim_time:=true
