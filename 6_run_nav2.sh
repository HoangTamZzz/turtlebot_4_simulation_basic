#!/bin/bash
# PHAN 4: Autonomous Navigation voi Nav2
echo "=========================================================="
echo " [PHAN 4] Khoi chay Nav2 Autonomous Navigation..."
echo "=========================================================="
source /home/hoangtam/.bashrc
source /opt/ros/humble/setup.bash

ros2 launch turtlebot4_navigation nav2.launch.py use_sim_time:=true
