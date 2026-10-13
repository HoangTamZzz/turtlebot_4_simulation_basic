#!/bin/bash
# Khoi chay RViz2 (Ho tro ca SLAM va Navigation)
source /home/hoangtam/.bashrc
source /opt/ros/humble/setup.bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$1" == "nav" ]; then
    echo "=========================================================="
    echo " [RViz2 - Navigation] Khoi chay RViz2 voi che do Nav2..."
    echo "=========================================================="
    CONFIG_FILE="$DIR/config/turtlebot4_nav.rviz"
else
    echo "=========================================================="
    echo " [RViz2 - SLAM] Khoi chay RViz2 voi che do SLAM..."
    echo "=========================================================="
    CONFIG_FILE="$DIR/config/turtlebot4_slam.rviz"
fi

export LIBGL_ALWAYS_SOFTWARE=1
export MESA_GL_VERSION_OVERRIDE=3.3

ros2 run rviz2 rviz2 -d "$CONFIG_FILE" --ros-args -p use_sim_time:=true
