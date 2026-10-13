#!/bin/bash
# Mo cua so truc quan 3D Gazebo (Ignition Gazebo GUI)
echo "=========================================================="
echo " [GAZEBO GUI] Dang mo cua so giao dien 3D Gazebo..."
echo "=========================================================="
source /home/hoangtam/.bashrc
source /opt/ros/humble/setup.bash

export LIBGL_ALWAYS_SOFTWARE=1
export IGN_GAZEBO_RESOURCE_PATH="/opt/ros/humble/share/turtlebot4_ignition_bringup/worlds:/opt/ros/humble/share/irobot_create_ignition_bringup/worlds:/opt/ros/humble/share"
export IGN_GUI_PLUGIN_PATH="/opt/ros/humble/share/turtlebot4_ignition_gui_plugins/lib:/opt/ros/humble/share/irobot_create_ignition_plugins/lib"

ign gazebo -g --gui-config /opt/ros/humble/share/turtlebot4_ignition_bringup/gui/standard/gui.config
