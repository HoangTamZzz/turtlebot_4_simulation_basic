#!/bin/bash
# PHAN 3: Localization bang AMCL voi ban do da tao
echo "=========================================================="
echo " [PHAN 3] Khoi chay AMCL Localization voi ban do da luu..."
echo "=========================================================="
source /home/hoangtam/.bashrc
source /opt/ros/humble/setup.bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAP_FILE="$DIR/maps/map.yaml"
PARAMS_FILE="$DIR/config/localization.yaml"

if [ ! -f "$MAP_FILE" ]; then
    echo "Khong tim thay ban do $MAP_FILE! Vui long chay 4_save_map.sh truoc."
    exit 1
fi

echo "-> Su dung ban do: $MAP_FILE"
echo "-> Tu dong khoi tao vi tri robot tai (0,0) (set_initial_pose: true)"
ros2 launch turtlebot4_navigation localization.launch.py map:="$MAP_FILE" params:="$PARAMS_FILE" use_sim_time:=true
