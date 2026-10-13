# Hướng Dẫn Thực Hiện Bài Tập TurtleBot 4 Simulation, SLAM & Nav2

Bài tập này hoàn thành trọn vẹn 4 phần yêu cầu:
1. **Phần 1 – Simulation**: Khởi chạy TurtleBot 4 trong Gazebo (Mở trực quan 3D Gazebo GUI với card đồ họa rời NVIDIA RTX 4060), kiểm tra các topic `/scan`, `/odom`, `/cmd_vel` và hiển thị trên RViz2.
2. **Phần 2 – Xây dựng bản đồ (SLAM)**: Sử dụng SLAM Toolbox tạo bản đồ 2D siêu tốc x2 (0.90 m/s), tự động bám giữa hành lang mê cung, lưu thành `map.yaml` và `map.pgm`.
3. **Phần 3 – Localization**: Nạp bản đồ đã lưu, khởi chạy AMCL và hội tụ vị trí robot.
4. **Phần 4 – Autonomous Navigation**: Điều hướng tự động Nav2, gửi Goal trong RViz2 hoặc qua script.

---

## Cấu trúc thư mục

```
TurtleBot 4 Simulation/
├── 0_cleanup.sh           # Dọn dẹp sạch toàn bộ tiến trình ROS 2 & Gazebo
├── 1_run_all.sh           # [KHUYÊN DÙNG] Gộp Gazebo 3D GUI + RViz2 + SLAM Toolbox vào 1 lệnh duy nhất!
├── 1_run_sim.sh           # Khởi chạy Simulation headless (Tùy chọn chạy tách rời)
├── 1b_run_gazebo_gui.sh   # Mở cửa sổ 3D Gazebo GUI độc lập
├── 2_run_rviz.sh          # Mở RViz2 độc lập
├── 3_run_slam.sh          # Mở SLAM Toolbox độc lập
├── 3b_auto_explorer.sh    # Tự động quét bản đồ thông minh x2 tốc độ (0.90 m/s, tự cân giữa hành lang)
├── 3c_teleop.sh           # Điều khiển thủ công bàn phím x2 tốc độ (0.92 m/s, Deadman Auto-Stop)
├── 4_save_map.sh          # Lưu bản đồ ra thư mục maps/
├── 5_run_localization.sh  # Khởi chạy AMCL Localization (Phần 3)
├── 6_run_nav2.sh          # Khởi chạy Nav2 Navigation (Phần 4)
├── config/
│   ├── slam.yaml          # File cấu hình SLAM Toolbox tối ưu tốc độ x2 (dt 0.12m, update 1.5s)
│   └── turtlebot4_slam.rviz # File cấu hình RViz2 siêu nhẹ, chống treo tuyệt đối
├── maps/
│   ├── map.yaml           # Metadata bản đồ
│   └── map.pgm            # Ảnh Occupancy Grid bản đồ
└── scripts/
    ├── auto_explorer.py   # Corridor Centering + Frontier Grid + Anti-Stuck Hazard (Sprint 0.90 m/s)
    ├── teleop_keyboard.py # Node điều khiển thủ công x2 (0.92 m/s, Deadman Auto-Stop, Bumper Recovery)
    └── 7_nav_to_goal.py   # Script gửi tọa độ Goal cho Nav2
```

---

## Hướng dẫn chạy mô phỏng

### BƯỚC 1: Khởi động Toàn bộ Mô phỏng (Gazebo 3D + RViz2 + SLAM)
Mở **Terminal 1**:
```bash
cd ~/ros2_ws/src/"TurtleBot 4 Simulation"
./1_run_all.sh
```
*Script sẽ tự động:*
1. Dọn dẹp toàn bộ tiến trình cũ.
2. Khởi động Gazebo Server và nạp Robot vào map.
3. Mở cửa sổ **Gazebo 3D GUI** trực quan.
4. Mở **RViz2** giám sát LiDAR và khung bản đồ.
5. Khởi động **SLAM Toolbox** sẵn sàng quét bản đồ.

---

### BƯỚC 2: Điều khiển Robot quét bản đồ (Tốc độ x2)
Mở **Terminal 2**:

- **Cách 1: Tự động lái quét siêu tốc**
  ```bash
  cd ~/ros2_ws/src/"TurtleBot 4 Simulation"
  ./3b_auto_explorer.sh
  ```
  *Tính năng vượt trội:*
  - **Phóng 0.90 m/s dọc hành lang:** Tự động phát hiện hành lang dài và phóng tốc độ gấp đôi.
  - **Tự động cân giữa hành lang (Corridor Centering):** Đo khoảng cách 2 bên tường và bám chính giữa, không bao giờ bị quẹt mép hay dừng giật cục.
  - **Chống kẹt tức thì:** Nhận tín hiệu cản va chạm Bumper, tự động lùi giải tỏa trong 0.05 giây.
  - Hoàn thành quét trọn vẹn bản đồ chỉ trong khoảng **1 đến 1.5 phút**!

- **Cách 2: Điều khiển thủ công bằng bàn phím**
  ```bash
  cd ~/ros2_ws/src/"TurtleBot 4 Simulation"
  ./3c_teleop.sh
  ```
  - Phím `1`: Mức chuẩn `0.46 m/s`
  - Phím `2`: Mức cao **`0.92 m/s`** (Mặc định)
  - Phím `3`: Mức Turbo `1.15 m/s`
  - Phím di chuyển: `W` (Tiến), `X` (Lùi), `A` (Rẽ trái), `D` (Rẽ phải), `S` hoặc `Space` (Dừng)
  - **Auto-Stop an toàn:** Buông tay khỏi phím robot sẽ tự động phanh dừng lại, không lo lao vào tường.
---

### BƯỚC 3: Lưu bản đồ khi đã quét xong
Khi bản đồ trên RViz2 đã kín và đẹp, nhấn `Ctrl+C` ở Terminal 2 để dừng quét, sau đó chạy:
```bash
./4_save_map.sh
```
Bản đồ sẽ được lưu sạch đẹp vào `maps/map.yaml` và `maps/map.pgm`.

---

### BƯỚC 4 & 5: Autonomous Navigation với Nav2 (Dẫn đường tự động)
Sau khi đã quét và lưu bản đồ ở Bước 3, để mở chế độ dẫn đường tự động theo bản đồ đã lưu:

**Cách 1: Chạy 1 lệnh duy nhất**
```bash
cd ~/ros2_ws/src/"TurtleBot 4 Simulation"
./1_run_nav2_all.sh
```
Lệnh này sẽ tự động khởi chạy Gazebo Server, Gazebo 3D, nạp bản đồ đã lưu, bật AMCL tự định vị tại (0,0), bật Nav2 và mở giao diện RViz2 Navigation sẵn sàng!

---

**Cách 2: Chạy riêng từng terminal (Truyền thống)**
```bash
./1_run_sim.sh          # Terminal 1: Khởi chạy mô phỏng Gazebo
./2b_run_rviz_nav.sh    # Terminal 2: Khởi chạy RViz2 chế độ Navigation (Fixed Frame: map)
./5_run_localization.sh # Terminal 3: Chạy AMCL (Tự động định vị robot tại 0,0)
./6_run_nav2.sh         # Terminal 4: Chạy bộ điều hướng Nav2 Stack
```

---

### CÁCH DÙNG NAV2 GOAL ĐIỀU KHIỂN ROBOT:
1. Bản đồ đã lưu hiển thị đầy đủ, sắc nét trên RViz2 (khung tọa độ gốc `map`).
2. Trên thanh công cụ trên cùng của RViz2, nhấp chuột vào công cụ **Nav2 Goal** (hoặc **2D Goal Pose**).
3. Nhấp chuột vào một khoảng trống trên đường đi trong bản đồ, giữ chuột và kéo nhẹ để chỉ hướng mũi tên robot quay mặt tới khi tới nơi.
4. Ngay lập tức:
   - Bộ lập kế hoạch toàn cục sẽ vẽ ra đường đi màu xanh (`/plan`) qua mê cung.
   - Robot sẽ tự động tăng tốc di chuyển theo quỹ đạo và né mọi bức tường để về đích chính xác!
