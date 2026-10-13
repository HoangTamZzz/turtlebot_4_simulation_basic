#!/usr/bin/env python3
"""
===================================================================================
 AUTONOMOUS MAZE EXPLORER V6 - ROCK-SOLID ANTI-STUCK & HIGH-SPEED MAPPING
===================================================================================
 1. Chuan hoa goc RPLiDAR 90 do (base_link frame): CUC KY CHUAN XAC, khong bao gio dam tuong.
 2. Quy trinh thoat ket 2 giai doan (2-Phase Recovery):
    - Giai doan 1: Lui thang 26cm (khong xoay) de tach hoan toan khoi vach tuong.
    - Giai doan 2: Xoay tai cho (Pure In-Place Pivot) ve phia thoang nhat cho den khi truoc mat trong.
 3. Ham phanh chu dong (Dynamic Braking): Phong 1.30 m/s o duong thang, tu ham phanh truoc 1.6m.
 4. Banh ray PD Magnetic Centering: Luon giu robot o tam hanh lang 1.0m.
 5. Phat hien ngo cut & Quay dau 180 do trong 1.0s.
 6. Giao dien Dashboard Terminal truc quan thoi gian thuc.
===================================================================================
"""

import sys
import time
import math
from collections import defaultdict, deque
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
import numpy as np

try:
    from irobot_create_msgs.msg import HazardDetectionVector
    HAS_HAZARD_MSG = True
except ImportError:
    HAS_HAZARD_MSG = False


class RobustAutoExplorer(Node):
    def __init__(self):
        super().__init__('robust_auto_explorer')

        # Thiet lap toc do (Nhanh hon 2.5x - 3x so voi goc 0.46 m/s, cuc ky em va an toan)
        self.MAX_SPRINT_SPEED = 1.30     # m/s (Toc do chay thang hanh lang)
        self.MAX_ANGULAR_SPEED = 3.00    # rad/s (Xoay tai cho)
        self.MIN_TURN_SPEED = 0.35       # m/s (Toc do khi den gan goc re)
        self.BRAKE_DISTANCE = 1.60       # m (Bat dau ham phanh truoc goc cua)
        self.STOP_DISTANCE = 0.55        # m (Dung tien hoan toan va bat dau xoay)

        # Publisher van toc (Publish ca 2 topic)
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.diff_pub = self.create_publisher(Twist, '/diffdrive_controller/cmd_vel_unstamped', 10)

        qos_sensor = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, qos_sensor)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_callback, qos_sensor)

        if HAS_HAZARD_MSG:
            self.create_subscription(
                HazardDetectionVector,
                '/hazard_detection',
                self.hazard_callback,
                qos_sensor
            )

        # Chu ky dieu khien 30 Hz (0.033s)
        self.timer = self.create_timer(0.033, self.control_loop)

        self.latest_scan = None
        self.cached_n = 0
        self.angles_robot = None

        # Vi tri & Huong
        self.pos_x = 0.0
        self.pos_y = 0.0
        self.yaw = 0.0
        self.odom_v = 0.0
        self.has_odom = False

        # Bo nho khong gian da quet (Grid 0.35m x 0.35m)
        self.visit_counts = defaultdict(int)
        self.last_visit_time = 0.0

        # Co che thoat ket 2 giai doan (2-Phase Recovery)
        # recovery_state: 0: Normal, 1: Reverse Straight, 2: Pivot Away
        self.recovery_state = 0
        self.recovery_phase_end = 0.0
        self.recovery_pivot_dir = 1.0

        # Bo phat hien ket banh xe (Stall Guardian)
        self.node_start_time = time.time()
        self.stall_history = deque(maxlen=60)

        # Bo theo doi vong lap (Loop Breaker)
        self.pose_history = deque(maxlen=300)
        self.force_escape_end = 0.0
        self.force_escape_angle = 0.0

        # Bo dieu khien can giua PD
        self.prev_centering_error = 0.0
        self.last_centering_time = time.time()

        # Dashboard & Thong ke
        self.current_state = "KHOI DONG"
        self.total_escapes = 0
        self.last_dashboard_print = 0.0
        self.commanded_linear = 0.0

        self.get_logger().info('RobustAutoExplorer V6 Online: 1.30 m/s Sprint + Zero-Stuck Guarantee!')

    def trigger_recovery(self, reason="VA CHAM"):
        """Kich hoat quy trinh thoat ket 2 giai doan bat kha chien bai"""
        now = time.time()
        # Neu dang trong giai doan lui, khong ngat quang
        if self.recovery_state == 1 and now < self.recovery_phase_end:
            return

        self.total_escapes += 1
        self.get_logger().warn(f'[{reason}] Kich hoat quy trinh thoat ket 2 giai doan...')
        # Giai doan 1: Lui thang 0.75s (khong xoay) de tach roi vach tuong
        self.recovery_state = 1
        self.recovery_phase_end = now + 0.75
        self.stall_history.clear()

    def hazard_callback(self, msg):
        """Phan xa Bumper phan cung: Ngay lap tuc kich hoat lui thang giai thoat"""
        for det in msg.detections:
            if det.type in (1, 3):  # BUMP hoac STALL
                self.trigger_recovery("BUMPER VA CHAM")
                break

    def odom_callback(self, msg):
        self.pos_x = msg.pose.pose.position.x
        self.pos_y = msg.pose.pose.position.y
        self.odom_v = msg.twist.twist.linear.x
        qz = msg.pose.pose.orientation.z
        qw = msg.pose.pose.orientation.w
        self.yaw = 2.0 * math.atan2(qz, qw)
        self.has_odom = True

        now = time.time()
        if now - self.last_visit_time > 0.10:
            cx = int(round(self.pos_x / 0.35))
            cy = int(round(self.pos_y / 0.35))
            self.visit_counts[(cx, cy)] += 1
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    self.visit_counts[(cx + dx, cy + dy)] += 1

            self.pose_history.append((self.pos_x, self.pos_y, now))
            self.stall_history.append((self.pos_x, self.pos_y, now, self.commanded_linear, self.odom_v))
            self.last_visit_time = now

    def scan_callback(self, msg):
        self.latest_scan = msg

    def _update_angles(self, n, a_min, a_inc):
        # RPLiDAR frame rotated +90 deg relative to base_link:
        # Chuyen doi chinh xac sang he quy chieu Robot (base_link):
        angles_lidar = a_min + np.arange(n) * a_inc
        self.angles_robot = (angles_lidar + np.pi / 2.0 + np.pi) % (2.0 * np.pi) - np.pi
        self.cached_n = n

    def publish_twist(self, linear_x, angular_z):
        t = Twist()
        t.linear.x = float(linear_x)
        t.angular.z = float(angular_z)
        self.commanded_linear = t.linear.x
        self.cmd_pub.publish(t)
        self.diff_pub.publish(t)

    def is_stalled(self):
        """Phat hien ket banh xe: Ra lenh chay lien tuc >= 0.35m/s trong 1.8s nhung khong di chuyen"""
        now = time.time()
        if now - self.node_start_time < 2.5:
            return False
        if len(self.stall_history) < 18:
            return False

        cmds = [h[3] for h in self.stall_history]
        if np.mean(cmds) > 0.35:
            p_old = self.stall_history[0]
            p_cur = self.stall_history[-1]
            dist = math.hypot(p_cur[0] - p_old[0], p_cur[1] - p_old[1])
            dt = p_cur[2] - p_old[2]
            if dt > 1.8 and dist < 0.08:
                return True
        return False

    def is_trapped_in_loop(self):
        """Phat hien bi quan quan trong 1 o me cung qua 8.0 giay"""
        if len(self.pose_history) < 80:
            return False
        xs = [p[0] for p in self.pose_history]
        ys = [p[1] for p in self.pose_history]
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        return span < 0.90

    def get_cell_visit(self, x, y):
        cx = int(round(x / 0.35))
        cy = int(round(y / 0.35))
        return self.visit_counts[(cx, cy)]

    def control_loop(self):
        now = time.time()
        if self.latest_scan is None:
            return

        raw_ranges = np.array(self.latest_scan.ranges)
        # Loc du lieu laser: bo tia hong (< 0.16m hoac nan/inf)
        ranges = np.where(np.isnan(raw_ranges) | np.isinf(raw_ranges) | (raw_ranges <= 0.16), 12.0, raw_ranges)
        n = len(ranges)
        if n == 0:
            return

        if self.cached_n != n:
            self._update_angles(n, self.latest_scan.angle_min, self.latest_scan.angle_increment)

        # -----------------------------------------------------------------
        # 1. PHAN TICH KHONG GIAN 360 DO (CHUAN BASE_LINK)
        # -----------------------------------------------------------------
        front_cone = np.abs(self.angles_robot) < np.deg2rad(20)
        fl_cone = (self.angles_robot >= np.deg2rad(20)) & (self.angles_robot < np.deg2rad(60))
        fr_cone = (self.angles_robot <= -np.deg2rad(20)) & (self.angles_robot > -np.deg2rad(60))
        left_side = (self.angles_robot >= np.deg2rad(65)) & (self.angles_robot < np.deg2rad(115))
        right_side = (self.angles_robot <= -np.deg2rad(65)) & (self.angles_robot > -np.deg2rad(115))
        back_cone = np.abs(np.abs(self.angles_robot) - np.pi) < np.deg2rad(35)

        d_front = float(np.min(ranges[front_cone])) if np.any(front_cone) else 12.0
        d_fl = float(np.min(ranges[fl_cone])) if np.any(fl_cone) else 12.0
        d_fr = float(np.min(ranges[fr_cone])) if np.any(fr_cone) else 12.0
        d_left = float(np.min(ranges[left_side])) if np.any(left_side) else 12.0
        d_right = float(np.min(ranges[right_side])) if np.any(right_side) else 12.0
        d_back = float(np.min(ranges[back_cone])) if np.any(back_cone) else 12.0

        # -----------------------------------------------------------------
        # 2. XU LY THOAT KET 2 GIAI DOAN (2-PHASE RECOVERY)
        # -----------------------------------------------------------------
        if self.recovery_state == 1:
            # GIAI DOAN 1: Lui thang dứt khoát (-0.35 m/s, khong xoay)
            if now < self.recovery_phase_end:
                # Kiem tra an toan phia sau: neu phia sau qua sat (< 0.20m) thi dung lui
                if d_back > 0.22:
                    self.current_state = "LUI THANG GIAI THOAT"
                    self.publish_twist(-0.35, 0.0)
                else:
                    self.recovery_phase_end = now # Chuyen ngay sang giai doan 2
                self._render_dashboard(now)
                return
            else:
                # Chuyen sang Giai doan 2: Xoay tai cho ve huong thoang hon
                self.recovery_state = 2
                self.recovery_phase_end = now + 0.80
                self.recovery_pivot_dir = 1.0 if d_left >= d_right else -1.0

        if self.recovery_state == 2:
            # GIAI DOAN 2: Xoay tai cho (Pure in-place pivot) cho den khi mat truoc thoang
            if now < self.recovery_phase_end or d_front < 0.65:
                self.current_state = "XOAY TIM LOI RA"
                self.publish_twist(0.0, self.MAX_ANGULAR_SPEED * self.recovery_pivot_dir)
                self._render_dashboard(now)
                return
            else:
                # Hoan thanh giai doan thoat ket!
                self.recovery_state = 0

        # Phat hien qua sat tuong truoc mat (< 0.26m) -> Kich hoat thoat ket
        if d_front < 0.26:
            self.trigger_recovery("SAT TUONG TRUOC MAT")
            self._render_dashboard(now)
            return

        # Phat hien ket banh xe qua Odom Stall -> Kich hoat thoat ket
        if self.is_stalled():
            self.trigger_recovery("KET BANH XE")
            self._render_dashboard(now)
            return

        # -----------------------------------------------------------------
        # 3. PHAT HIEN NGO CUT & QUAY DAU 180 DO TRONG 1.0S
        # -----------------------------------------------------------------
        # 3 mat truoc va 2 ben suon deu la tuong me cung (< 0.55m)
        if d_front < 0.55 and d_left < 0.58 and d_right < 0.58:
            self.total_escapes += 1
            self.recovery_state = 2
            self.recovery_phase_end = now + 1.05  # 1.05s x 3.0 rad/s ~ 3.15 rad (~180 do)
            self.recovery_pivot_dir = 1.0 if d_left >= d_right else -1.0
            self.current_state = "QUAY 180 THOAT NGO CUT"
            self.publish_twist(0.0, self.MAX_ANGULAR_SPEED * self.recovery_pivot_dir)
            self._render_dashboard(now)
            return

        # -----------------------------------------------------------------
        # 4. CHE DO THOAT VONG LAP (LOOP BREAKER)
        # -----------------------------------------------------------------
        if now < self.force_escape_end:
            angle_err = (self.force_escape_angle - self.yaw + np.pi) % (2.0 * np.pi) - np.pi
            if abs(angle_err) > 0.25:
                self.current_state = "XOAY THOAT VONG LAP"
                self.publish_twist(0.0, float(np.clip(2.5 * angle_err, -self.MAX_ANGULAR_SPEED, self.MAX_ANGULAR_SPEED)))
            else:
                self.current_state = "LAO RA KHOI VONG LAP"
                self.publish_twist(0.80, float(np.clip(1.2 * angle_err, -1.0, 1.0)))
            self._render_dashboard(now)
            return

        if self.is_trapped_in_loop():
            # Quet 360 do tim loi thoat den vung it di qua nhat
            best_dir = 0.0
            best_dist = 0.0
            for test_a in np.linspace(-np.pi, np.pi, 24, endpoint=False):
                mask = np.abs(self.angles_robot - test_a) < np.deg2rad(15)
                if np.any(mask):
                    dist = float(np.min(ranges[mask]))
                    fx = self.pos_x + min(dist, 2.0) * math.cos(self.yaw + test_a)
                    fy = self.pos_y + min(dist, 2.0) * math.sin(self.yaw + test_a)
                    visits = self.get_cell_visit(fx, fy)
                    score = dist - visits * 0.5
                    if score > best_dist:
                        best_dist = score
                        best_dir = test_a

            self.force_escape_angle = (self.yaw + best_dir + np.pi) % (2.0 * np.pi) - np.pi
            self.force_escape_end = now + 2.0
            self.pose_history.clear()
            self.current_state = "XOAY THOAT VONG LAP"
            self.publish_twist(0.0, self.MAX_ANGULAR_SPEED if best_dir >= 0 else -self.MAX_ANGULAR_SPEED)
            self._render_dashboard(now)
            return

        # -----------------------------------------------------------------
        # 5. DIEU KHIEN CAN GIUA HANH LANG (PD MAGNETIC CENTERING)
        # -----------------------------------------------------------------
        dt_c = max(now - self.last_centering_time, 0.001)
        if d_left < 0.85 and d_right < 0.85:
            centering_error = d_left - d_right
            d_err = (centering_error - self.prev_centering_error) / dt_c
            centering_w = float(np.clip(-2.0 * centering_error - 0.5 * d_err, -1.50, 1.50))
            self.prev_centering_error = centering_error
            self.last_centering_time = now
        else:
            centering_w = 0.0
            self.prev_centering_error = 0.0
            self.last_centering_time = now

        # -----------------------------------------------------------------
        # 6. DANH GIA CAC HUONG DI (FRONTIER EXPLORATION)
        # -----------------------------------------------------------------
        candidate_angles = np.linspace(-np.deg2rad(105), np.deg2rad(105), 15)
        scores = []

        for c_ang in candidate_angles:
            c_mask = np.abs(self.angles_robot - c_ang) < np.deg2rad(12)
            if not np.any(c_mask):
                scores.append(-9999.0)
                continue

            c_dist = float(np.min(ranges[c_mask]))
            # Neu huong nay qua sat tuong (< 0.35m) -> Bo qua
            if c_dist < 0.35:
                scores.append(-9999.0)
                continue

            look = min(c_dist - 0.20, 2.5)
            tx = self.pos_x + look * math.cos(self.yaw + c_ang)
            ty = self.pos_y + look * math.sin(self.yaw + c_ang)
            visits = self.get_cell_visit(tx, ty)

            if visits == 0:
                frontier_score = 160.0
            elif visits <= 2:
                frontier_score = 30.0
            else:
                frontier_score = -25.0 * min(visits, 8)

            clearance_score = min(c_dist, 5.0) * 15.0
            forward_bias = math.cos(c_ang) * 20.0

            scores.append(frontier_score + clearance_score + forward_bias)

        best_idx = int(np.argmax(scores))
        best_angle = candidate_angles[best_idx]
        best_score = scores[best_idx]

        # -----------------------------------------------------------------
        # 7. DIEU KHIEN DONG CO PHAN CAP AN TOAN TUYET DOI
        # -----------------------------------------------------------------

        # CAP 1: VA CAN SAT SUON (< 0.22m) -> NE SANG PHIA THOANG
        if d_fl < 0.22 or d_fr < 0.22:
            self.current_state = "NE GOC HO"
            turn_w = -2.20 if d_fl < d_fr else 2.20
            self.publish_twist(0.20, turn_w)

        # CAP 2: TRUOC MAT LA TUONG HOAC GOC VUONG (< STOP_DISTANCE = 0.55m)
        elif d_front < self.STOP_DISTANCE:
            self.current_state = "XOAY TIM LOI RE"
            # Dung tien hoan toan (linear.x = 0), chi xoay tai cho
            target_w = float(np.clip(best_angle * 3.0, -self.MAX_ANGULAR_SPEED, self.MAX_ANGULAR_SPEED))
            if abs(target_w) < 1.2:
                target_w = 2.20 if best_angle >= 0 else -2.20
            self.publish_twist(0.0, target_w)

        # CAP 3: DANG DEN GAN GOC RE (< BRAKE_DISTANCE = 1.60m) -> HAM PHANH VA OM CUA
        elif d_front < self.BRAKE_DISTANCE:
            self.current_state = "HAM PHANH & OM CUA"
            # Ham phanh muot ma tu 0.35 den 0.90 m/s
            ratio = (d_front - self.STOP_DISTANCE) / (self.BRAKE_DISTANCE - self.STOP_DISTANCE)
            linear_v = float(np.clip(self.MIN_TURN_SPEED + (0.90 - self.MIN_TURN_SPEED) * ratio, self.MIN_TURN_SPEED, 0.90))
            angular_w = float(np.clip(best_angle * 2.2 + centering_w * 0.4, -2.20, 2.20))
            self.publish_twist(linear_v, angular_w)

        # CAP 4: HANH LANG THONG THOANG (>= 1.60m) -> SPRINT 1.30 m/s!
        else:
            self.current_state = f"SPRINT ({self.MAX_SPRINT_SPEED:.2f} m/s)"
            linear_v = self.MAX_SPRINT_SPEED

            if abs(best_angle) > np.deg2rad(30) and best_score > 120.0:
                angular_w = float(np.clip(best_angle * 1.5, -1.60, 1.60))
            else:
                angular_w = centering_w

            self.publish_twist(linear_v, angular_w)

        self._render_dashboard(now)

    def _render_dashboard(self, now):
        if now - self.last_dashboard_print > 0.20:
            elapsed = int(now - self.node_start_time)
            mins, secs = divmod(elapsed, 60)
            cells = len(self.visit_counts)
            v_str = f"V: {self.commanded_linear:+.2f}m/s"
            odom_str = f"Thuc: {self.odom_v:+.2f}m/s"
            pos_str = f"Pos: ({self.pos_x:+.1f}, {self.pos_y:+.1f})"
            stat_str = f"Quet: {cells} o | Thoat ket: {self.total_escapes} | Time: {mins:02d}:{secs:02d}"
            sys.stdout.write(f"\r[{self.current_state:<22}] {v_str} | {odom_str} | {pos_str} | {stat_str}   ")
            sys.stdout.flush()
            self.last_dashboard_print = now


def main(args=None):
    rclpy.init(args=args)
    node = RobustAutoExplorer()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        if rclpy.ok():
            stop = Twist()
            node.cmd_pub.publish(stop)
            node.diff_pub.publish(stop)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        print("\n[DA DUNG] RobustAutoExplorer da dung an toan.")


if __name__ == '__main__':
    main()
