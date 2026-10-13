#!/bin/bash
# ==============================================================================
#  ALL-IN-ONE LAUNCH: GAZEBO 3D GUI + RVIZ2 + SLAM TOOLBOX
#  Khoi chay toan bo he thong mo phong chi voi 1 lenh duy nhat!
# ==============================================================================
echo "=================================================================="
echo " [ALL-IN-ONE] DANG KHOI CHAY GAZEBO 3D + RVIZ2 + SLAM TOOLBOX..."
echo "=================================================================="

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Don dep sach se cac tien trinh cu
bash "$DIR/0_cleanup.sh" >/dev/null 2>&1
sleep 1

source /home/hoangtam/.bashrc
source /opt/ros/humble/setup.bash

export XDG_RUNTIME_DIR="/tmp/runtime-$USER"
mkdir -p "$XDG_RUNTIME_DIR" 2>/dev/null && chmod 700 "$XDG_RUNTIME_DIR" 2>/dev/null

export IGN_GAZEBO_RESOURCE_PATH="/opt/ros/humble/share/turtlebot4_ignition_bringup/worlds:/opt/ros/humble/share/irobot_create_ignition_bringup/worlds:/opt/ros/humble/share"
export IGN_GUI_PLUGIN_PATH="/opt/ros/humble/share/turtlebot4_ignition_gui_plugins/lib:/opt/ros/humble/share/irobot_create_ignition_plugins/lib"

# Chi don dep khi nguoi dung chu dong nhan Ctrl+C (SIGINT hoac SIGTERM)
cleanup() {
    echo ""
    echo "=================================================================="
    echo " [DUNG HE THONG] Dang dong tat ca tien trinh..."
    kill $(jobs -p) >/dev/null 2>&1
    bash "$DIR/0_cleanup.sh" >/dev/null 2>&1
    echo " Da dong toan bo he thong thanh cong."
    echo "=================================================================="
    exit 0
}
trap cleanup SIGINT SIGTERM

# 2. KHOI CHAY GAZEBO SIMULATION SERVER & ROBOT
echo "-> [1/4] Dang khoi chay Gazebo Simulation Server & Robot..."
WORLD="${1:-depot}"
echo "-> [1/4] Dang khoi chay Gazebo Simulation Server & Robot (World: $WORLD)..."
ros2 launch turtlebot4_ignition_bringup turtlebot4_ignition.launch.py world:="$WORLD" &

echo "-> Dang cho Robot spawn va diffdrive_controller san sang..."
count=0
while ! ros2 topic list 2>/dev/null | grep -q "^/odom$"; do
    sleep 1
    count=$((count+1))
    if [ $count -eq 10 ] || [ $count -eq 18 ]; then
        echo "-> [Tu dong tro giup] Dang kich hoat diffdrive_controller..."
        ros2 run controller_manager spawner diffdrive_controller >/dev/null 2>&1 &
    fi
    if [ $count -ge 30 ]; then
        break
    fi
done
sleep 2
echo "-> Robot va diffdrive_controller da SAN SANG 100%!"

# 3. KHOI CHAY SLAM TOOLBOX (Cau hinh toc do cao)
echo "-> [2/4] Dang khoi chay SLAM Toolbox..."
ros2 launch turtlebot4_navigation slam.launch.py params:="$DIR/config/slam.yaml" sync:=false use_sim_time:=true &

sleep 2

# 4. KHOI CHAY GAZEBO 3D GUI (On dinh chong crash driver)
echo "-> [3/4] Dang mo Cua so 3D Gazebo GUI..."
(
    export LIBGL_ALWAYS_SOFTWARE=1
    ign gazebo -g --gui-config /opt/ros/humble/share/turtlebot4_ignition_bringup/gui/standard/gui.config
) &

sleep 2

# 5. KHOI CHAY RVIZ2 (OpenGL chuan hoa, shader da duoc fix triet de)
echo "-> [4/4] Dang mo RViz2..."
(
    export LIBGL_ALWAYS_SOFTWARE=1
    export QT_QPA_PLATFORM=xcb
    CONFIG_FILE="$DIR/config/turtlebot4_slam.rviz"
    ros2 run rviz2 rviz2 -d "$CONFIG_FILE" --ros-args -p use_sim_time:=true
) &

echo ""
echo "=================================================================="
echo " [HOAN TAT] TOAN BO HE THONG DA KHOI CHAY THANH CONG!"
echo " - Gazebo Server: DANG CHAY (Vat ly toc do cao)"
echo " - Gazebo 3D GUI: DANG CHAY (On dinh chong vang)"
echo " - SLAM Toolbox:  DANG CHAY (San sang tao ban do)"
echo " - RViz2:         DANG CHAY (Hien thi ban do & robot)"
echo ""
echo " >>> MO TERMINAL 2 VA CHAY 1 TRONG 2 LENH DE DIEU KHIEN ROBOT: <<<"
echo "   1. Tu dong quet sieu toc:  ./3b_auto_explorer.sh"
echo "   2. Lai bang ban phim:      ./3c_teleop.sh"
echo ""
echo " (Nhan Ctrl+C tai terminal nay de dong tat ca tien trinh cung luc)"
echo "=================================================================="

# Cho tien trinh chay on dinh
wait
