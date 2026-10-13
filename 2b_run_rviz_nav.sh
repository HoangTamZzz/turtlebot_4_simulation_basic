#!/bin/bash
# Khoi chay RViz2 che do Navigation (Fixed Frame: map, hien thi map da luu, cong cu Nav2 Goal)
echo "=========================================================="
echo " [RViz2 - Navigation] Khoi chay RViz2 Navigation..."
echo "=========================================================="
source /home/hoangtam/.bashrc
source /opt/ros/humble/setup.bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$DIR/config/turtlebot4_nav.rviz"

export LIBGL_ALWAYS_SOFTWARE=1
export MESA_GL_VERSION_OVERRIDE=3.3

ros2 run rviz2 rviz2 -d "$CONFIG_FILE" --ros-args -p use_sim_time:=true
