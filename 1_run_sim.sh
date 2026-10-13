#!/bin/bash
# PHAN 1: Khoi chay TurtleBot 4 trong Gazebo (Server toc do cao, on dinh tuyet doi)
echo "=========================================================="
echo " [PHAN 1] Khoi chay TurtleBot 4 Simulation trong Gazebo..."
echo "=========================================================="
source /home/hoangtam/.bashrc
source /opt/ros/humble/setup.bash

# Tu dong don dep tien trinh cu truoc khi khoi dong de Controller luon spawn thanh cong 100%
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$DIR/0_cleanup.sh" >/dev/null 2>&1
sleep 1

export IGN_GAZEBO_RESOURCE_PATH="/opt/ros/humble/share/turtlebot4_ignition_bringup/worlds:/opt/ros/humble/share/irobot_create_ignition_bringup/worlds:/opt/ros/humble/share"
export IGN_GUI_PLUGIN_PATH="/opt/ros/humble/share/turtlebot4_ignition_gui_plugins/lib:/opt/ros/humble/share/irobot_create_ignition_plugins/lib"

echo "-> Simulation Server dang khoi dong (Real-Time Factor 1.0)..."
echo "-> [MEO] Neu ban muon xem them cua so 3D Gazebo, hay mo terminal moi va chay: ./1b_run_gazebo_gui.sh"
echo "=========================================================="

ros2 launch turtlebot4_ignition_bringup turtlebot4_ignition.launch.py world:=depot
