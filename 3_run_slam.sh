#!/bin/bash
# PHAN 2: Xay dung ban do bang SLAM Toolbox (Toi uu hoa chong treo/do RViz2)
echo "=========================================================="
echo " [PHAN 2] Khoi chay SLAM Toolbox toi uu hoa..."
echo "=========================================================="
source /home/hoangtam/.bashrc
source /opt/ros/humble/setup.bash

CONFIG_FILE="/home/hoangtam/ros2_ws/src/TurtleBot 4 Simulation/config/slam.yaml"

ros2 launch turtlebot4_navigation slam.launch.py params:="$CONFIG_FILE" sync:=false use_sim_time:=true
