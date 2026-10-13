#!/bin/bash
# ==============================================================================
#  ALL-IN-ONE LAUNCH: GAZEBO 3D GUI + RVIZ2 + AMCL LOCALIZATION + NAV2
#  Khoi chay toan bo he thong dan duong tu dong chi voi 1 lenh duy nhat!
# ==============================================================================
echo "=================================================================="
echo " [ALL-IN-ONE NAV2] DANG KHOI CHAY GAZEBO + AMCL + NAV2 + RVIZ..."
echo "=================================================================="

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAP_FILE="$DIR/maps/map.yaml"
PARAMS_FILE="$DIR/config/localization.yaml"
NAV2_PARAMS="$DIR/config/nav2.yaml"

if [ ! -f "$MAP_FILE" ]; then
    echo "[LOI] Khong tim thay ban do $MAP_FILE! Vui long chay tao va luu ban do truoc (./4_save_map.sh)."
    exit 1
fi

# 1. Don dep sach se cac tien trinh cu
bash "$DIR/0_cleanup.sh" >/dev/null 2>&1
sleep 1

source /home/hoangtam/.bashrc
source /opt/ros/humble/setup.bash

export XDG_RUNTIME_DIR="/tmp/runtime-$USER"
mkdir -p "$XDG_RUNTIME_DIR" 2>/dev/null && chmod 700 "$XDG_RUNTIME_DIR" 2>/dev/null

export IGN_GAZEBO_RESOURCE_PATH="/opt/ros/humble/share/turtlebot4_ignition_bringup/worlds:/opt/ros/humble/share/irobot_create_ignition_bringup/worlds:/opt/ros/humble/share"
export IGN_GUI_PLUGIN_PATH="/opt/ros/humble/share/turtlebot4_ignition_gui_plugins/lib:/opt/ros/humble/share/irobot_create_ignition_plugins/lib"

cleanup() {
    echo ""
    echo "=================================================================="
    echo " [DUNG HE THONG] Dang dong tat ca tien trinh Navigation..."
    kill $(jobs -p) >/dev/null 2>&1
    bash "$DIR/0_cleanup.sh" >/dev/null 2>&1
    echo " Da dong toan bo he thong thanh cong."
    echo "=================================================================="
    exit 0
}
trap cleanup SIGINT SIGTERM

# 2. KHOI CHAY GAZEBO SIMULATION SERVER & ROBOT
# Mac dinh dung 'maze' de khop 100% voi ban do map.yaml da luu
WORLD="${1:-depot}"
echo "-> [1/5] Dang khoi chay Gazebo Simulation Server & Robot (World: $WORLD)..."
ros2 launch turtlebot4_ignition_bringup turtlebot4_ignition.launch.py world:="$WORLD" &

# Cho den khi Robot spawn xong va diffdrive_controller bat dau phat /odom
echo "-> Dang cho Robot spawn va diffdrive_controller san sang..."
count=0
while ! ros2 topic list 2>/dev/null | grep -q "^/odom$"; do
    sleep 1
    count=$((count+1))
    # Neu sau 10 giay ma chua co /odom do may ban tai mesh, tu dong tro giup spawn lai
    if [ $count -eq 10 ] || [ $count -eq 18 ]; then
        echo "-> [Tu dong tro giup] Dang kich hoat diffdrive_controller..."
        ros2 run controller_manager spawner diffdrive_controller >/dev/null 2>&1 &
    fi
    if [ $count -ge 30 ]; then
        echo "-> Da het thoi gian cho, tiep tuc tien trinh..."
        break
    fi
done
sleep 2
echo "-> Robot va bo dieu khien banh xe da SAN SANG (TF odom -> base_link OK)!"

# 3. KHOI CHAY AMCL LOCALIZATION (Tu dong dinh vi robot tai 0,0)
echo "-> [2/5] Dang khoi chay AMCL Localization voi ban do da luu ($MAP_FILE)..."
ros2 launch turtlebot4_navigation localization.launch.py map:="$MAP_FILE" params:="$PARAMS_FILE" use_sim_time:=true &

sleep 2

# 4. KHOI CHAY NAV2 AUTONOMOUS NAVIGATION
echo "-> [3/5] Dang khoi chay bo dieu huong Nav2..."
ros2 launch turtlebot4_navigation nav2.launch.py params_file:="$NAV2_PARAMS" use_sim_time:=true &

# Cho cho den khi Nav2 Lifecycle chuyen sang Active hoan toan (tranh treo RViz2 khi dat Goal)
echo "-> Dang cho Nav2 Stack va AMCL khoi dong san sang (khoang 6-10s)..."
nav_count=0
while ! ros2 topic list 2>/dev/null | grep -q "/plan"; do
    sleep 1
    nav_count=$((nav_count+1))
    if [ $nav_count -ge 18 ]; then
        break
    fi
done
sleep 2
echo "-> Nav2 Stack & AMCL da SAN SANG 100%!"

# 5. KHOI CHAY GAZEBO 3D GUI
echo "-> [4/5] Dang mo Cua so 3D Gazebo GUI..."
(
    export LIBGL_ALWAYS_SOFTWARE=1
    ign gazebo -g --gui-config /opt/ros/humble/share/turtlebot4_ignition_bringup/gui/standard/gui.config
) &

sleep 2

# 6. KHOI CHAY RVIZ2 NAVIGATION (Fixed Frame: map, cong cu 2D Goal Pose)
echo "-> [5/5] Dang mo RViz2 Navigation..."
(
    export LIBGL_ALWAYS_SOFTWARE=1
    export QT_QPA_PLATFORM=xcb
    CONFIG_FILE="$DIR/config/turtlebot4_nav.rviz"
    ros2 run rviz2 rviz2 -d "$CONFIG_FILE" --ros-args -p use_sim_time:=true
) &

echo ""
echo "=================================================================="
echo " [HOAN TAT] HE THONG NAVIGATION DA SAN SANG!"
echo " - Ban do va RobotModel da duoc hien thi chuan 100% tren RViz2."
echo ""
echo " >>> HUONG DAN DUNG GOAL DIEU KHIEN ROBOT: <<<"
echo " 1. Tren thanh cong cu RViz2, nhap chon '2D Goal Pose' (hoac 'Nav2 Goal')."
echo " 2. Nhap chuot vao 1 vi tri trong tren ban do va keo chuot de chon huong toi."
echo " 3. Duong di mau xanh (/plan) se xuat hien va robot tu dong chay toi dich!"
echo ""
echo " (Nhan Ctrl+C tai terminal nay de dong tat ca tien trinh cung luc)"
echo "=================================================================="

wait
