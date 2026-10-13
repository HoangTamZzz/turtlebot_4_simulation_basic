#!/bin/bash
echo "Dang don dep toan bo tien trinh ROS 2 va Gazebo..."
killall -9 -q ruby rviz2 parameter_bridge ign gz slam_toolbox sync_slam_toolbox_node async_slam_toolbox_node \
    turtlebot4_node motion_control sensors_node hazards_vector_publisher ir_intensity_vector_publisher \
    wheel_status_publisher robot_state mock_publisher kidnap_estimator_publisher ui_mgr pose_republisher_node \
    interface_buttons_node turtlebot4_ignition_hmi_node robot_state_publisher joint_state_publisher \
    static_transform_publisher map_server amcl controller_server planner_server behavior_server \
    bt_navigator lifecycle_manager velocity_smoother waypoint_follower smoother_server spawner 2>/dev/null || true

pkill -9 -f "ros2 launch" 2>/dev/null || true
pkill -9 -f "ros2 run" 2>/dev/null || true
pkill -9 -f "ign gazebo" 2>/dev/null || true
pkill -9 -f "auto_explorer.py" 2>/dev/null || true
pkill -9 -f "teleop_keyboard.py" 2>/dev/null || true
pkill -9 -f "teleop_twist_keyboard" 2>/dev/null || true
pkill -9 -f "/opt/ros/humble/lib/nav2" 2>/dev/null || true
sleep 1
echo "Da don dep sach se! San sang khoi dong lai."
exit 0
