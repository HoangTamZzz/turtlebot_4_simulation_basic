#!/usr/bin/env python3
"""
Dieu khien thu cong TurtleBot 4 bang ban phim (Keyboard Teleoperation - HIGH SPEED & ANTI-STUCK)
=================================================================================================
- Toc do hanh trinh x2: Mac dinh 0.92 m/s (Co the chon 0.46, 0.92, 1.15 m/s bang phim 1, 2, 3)
- Che do Auto-Stop khi buong phim (Deadman switch) giup tranh dam thang vao tuong khi quen nha tay
- Co che Chong ket tuong & Chong treo Gazebo (Bumper Anti-Stuck & Auto-Disengage): Tu dong ngat ga
  va lui nhe khi cham tuong giup giu nguyen Real-Time Factor (RTF = 1.0) khong bi do mo phong
- Ho tro ca: Phim WASD, Phim mui ten (Up/Down/Left/Right), Phim IJKL, va bo go Unikey tieng Viet (u, w, a, s, d)
=================================================================================================
"""

import sys
import time
import select
import termios
import tty
import threading
import subprocess
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import Twist

try:
    from irobot_create_msgs.msg import HazardDetectionVector
    HAS_HAZARD_MSG = True
except ImportError:
    HAS_HAZARD_MSG = False

BANNER = """
====================================================================
  DIEU KHIEN THU CONG TURTLEBOT 4 (X2 SPEED: 0.92 m/s & ANTI-STUCK)
====================================================================
 [Phim di chuyen]:
       [W]  hoac  [Mui Ten Len]    hoac  [I] : TIEN TOI
       [X]  hoac  [Mui Ten Xuong]  hoac  [,] : LUI LAI
       [A]  hoac  [Mui Ten Trai]   hoac  [J] : RE TRAI
       [D]  hoac  [Mui Ten Phai]   hoac  [L] : RE PHAI
       [S]  hoac  [Space]          hoac  [K] : DUNG LAI (Phanh)

 [Chon muc toc do nhanh]:
   * 1 : Chuan Create 3 (0.46 m/s - 1x)
   * 2 : Toc do cao khuyen dung (0.92 m/s - 2x) [MAC DINH]
   * 3 : Turbo Sprint (1.15 m/s - 2.5x)
   * q / z : Tang / Giam toc do tien lui (+/- 10%)
   * e / c : Tang / Giam toc do xoay (+/- 10%)

 [Che do lai (Nhan phim P de doi)]:
   * p : Chuyen giua [Auto-Stop (Nha tay tu dung)] va [Cruise (Giu ga tu dong)]

 [Thoat]: Nhan Ctrl+C
====================================================================
"""

MOVE_BINDINGS = {
    # Turtlebot default IJKL
    'i': (1.0, 0.0, 'TIEN TOI'),
    'I': (1.0, 0.0, 'TIEN TOI'),
    ',': (-0.6, 0.0, 'LUI LAI'),
    'j': (0.0, 1.0, 'RE TRAI'),
    'J': (0.0, 1.0, 'RE TRAI'),
    'l': (0.0, -1.0, 'RE PHAI'),
    'L': (0.0, -1.0, 'RE PHAI'),
    'u': (0.8, 0.8, 'TIEN CHECH TRAI'),
    'U': (0.8, 0.8, 'TIEN CHECH TRAI'),
    'o': (0.8, -0.8, 'TIEN CHECH PHAI'),
    'O': (0.8, -0.8, 'TIEN CHECH PHAI'),
    'm': (-0.6, 0.8, 'LUI CHECH TRAI'),
    'M': (-0.6, 0.8, 'LUI CHECH TRAI'),
    '.': (-0.6, -0.8, 'LUI CHECH PHAI'),
    'k': (0.0, 0.0, 'DUNG LAI'),
    'K': (0.0, 0.0, 'DUNG LAI'),

    # WASD & Mui ten
    'w': (1.0, 0.0, 'TIEN TOI'),
    'W': (1.0, 0.0, 'TIEN TOI'),
    'x': (-0.6, 0.0, 'LUI LAI'),
    'X': (-0.6, 0.0, 'LUI LAI'),
    'a': (0.0, 1.0, 'RE TRAI'),
    'A': (0.0, 1.0, 'RE TRAI'),
    'd': (0.0, -1.0, 'RE PHAI'),
    'D': (0.0, -1.0, 'RE PHAI'),
    's': (0.0, 0.0, 'DUNG LAI'),
    'S': (0.0, 0.0, 'DUNG LAI'),
    ' ': (0.0, 0.0, 'DUNG LAI (STOP)'),

    # Arrow keys
    'KEY_UP': (1.0, 0.0, 'TIEN TOI'),
    'KEY_DOWN': (-0.6, 0.0, 'LUI LAI'),
    'KEY_LEFT': (0.0, 1.0, 'RE TRAI'),
    'KEY_RIGHT': (0.0, -1.0, 'RE PHAI'),

    # Ho tro khi bat Unikey go nham tieng Viet
    'ư': (1.0, 0.0, 'TIEN TOI'),
    'Ư': (1.0, 0.0, 'TIEN TOI'),
    'ơ': (0.8, -0.8, 'TIEN CHECH PHAI'),
    'đ': (0.0, -1.0, 'RE PHAI'),
    'Đ': (0.0, -1.0, 'RE PHAI'),
}


def unlock_controller_limits_worker():
    """Mo khoa gioi han van toc 0.46 cua diffdrive_controller trong Gazebo"""
    for _ in range(5):
        time.sleep(1.0)
        try:
            p1 = subprocess.run(
                ["ros2", "param", "set", "/diffdrive_controller", "linear.x.max_velocity", "1.20"],
                capture_output=True, timeout=2.0
            )
            p2 = subprocess.run(
                ["ros2", "param", "set", "/diffdrive_controller", "linear.x.max_acceleration", "3.0"],
                capture_output=True, timeout=2.0
            )
            p3 = subprocess.run(
                ["ros2", "param", "set", "/diffdrive_controller", "angular.z.max_velocity", "2.50"],
                capture_output=True, timeout=2.0
            )
            if b"Set parameter successful" in p1.stdout:
                break
        except Exception:
            pass


class TeleopKeyboardNode(Node):
    def __init__(self):
        super().__init__('teleop_keyboard')
        
        # Publisher van toc (Publish ca 2 topic de chac chan moi thanh phan nhan duoc)
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        self.pub_diff = self.create_publisher(Twist, '/diffdrive_controller/cmd_vel_unstamped', 10)

        # Cấu hình tốc độ x2 mặc định: 0.92 m/s và góc quay 2.20 rad/s
        self.linear_speed = 0.92
        self.angular_speed = 2.20
        
        self.target_linear = 0.0
        self.target_angular = 0.0
        self.current_state = 'DUNG YEN'

        # Che do lai: True = Auto-Stop khi nha tay (Deadman switch); False = Cruise (Giu ga)
        self.deadman_mode = True
        self.last_key_time = time.time()
        self.key_timeout = 0.60  # Tang len 0.60 giay de giu xe muot hon, khong giat cuc

        # Chống kẹt vật lý khi va chạm tường
        self.in_collision_recovery = False
        self.recovery_end_time = 0.0

        # Lắng nghe cảm biến va chạm cản trước (Bumper Hazard)
        if HAS_HAZARD_MSG:
            qos_hazard = QoSProfile(
                reliability=ReliabilityPolicy.BEST_EFFORT,
                history=HistoryPolicy.KEEP_LAST,
                depth=5
            )
            self.create_subscription(
                HazardDetectionVector,
                '/hazard_detection',
                self.hazard_callback,
                qos_hazard
            )

        # Timer phat van toc lien tuc 20 Hz
        self.timer = self.create_timer(0.05, self.publish_velocity)
        
        # Khoi dong tien trinh mo khoa van toc phan cung trong Gazebo
        threading.Thread(target=unlock_controller_limits_worker, daemon=True).start()
        self.get_logger().info('Teleop Keyboard Node started with 2x High-Speed & Anti-Stuck protection.')

    def hazard_callback(self, msg):
        """Phat hien va cham bumper voi tuong -> Tu dong nha ga va lui nhe giai toa va cham"""
        if self.in_collision_recovery:
            return

        for det in msg.detections:
            # Type 1 = BUMP, Type 3 = STALL
            if det.type in (1, 3) and self.target_linear > 0.0:
                self.get_logger().warn('[VA CHAM TUONG] Phat hien cham tuong! Tu dong ngat ga va lui nhe...')
                self.in_collision_recovery = True
                self.recovery_end_time = time.time() + 0.35
                self.target_linear = -0.22
                self.target_angular = 0.0
                self.current_state = 'LUI GIAI TOA'
                break

    def set_motion(self, lin_factor, ang_factor, state_label):
        self.in_collision_recovery = False
        self.target_linear = float(lin_factor * self.linear_speed)
        self.target_angular = float(ang_factor * self.angular_speed)
        self.current_state = state_label
        self.last_key_time = time.time()
        # Phat ngay tuc thi khong can doi timer
        msg = Twist()
        msg.linear.x = self.target_linear
        msg.angular.z = self.target_angular
        self.pub_cmd_vel.publish(msg)
        self.pub_diff.publish(msg)

    def set_preset_speed(self, lin, ang, label):
        self.linear_speed = lin
        self.angular_speed = ang
        if self.target_linear > 0:
            self.target_linear = self.linear_speed
        elif self.target_linear < 0:
            self.target_linear = -self.linear_speed * 0.6
        if self.target_angular > 0:
            self.target_angular = self.angular_speed
        elif self.target_angular < 0:
            self.target_angular = -self.angular_speed

    def adjust_speed(self, lin_mult, ang_mult):
        self.linear_speed = max(0.10, min(1.20, self.linear_speed * lin_mult))
        self.angular_speed = max(0.20, min(2.80, self.angular_speed * ang_mult))

    def toggle_deadman(self):
        self.deadman_mode = not self.deadman_mode
        return self.deadman_mode

    def publish_velocity(self):
        now = time.time()

        # Xu ly ket thuc lui giai toa va cham
        if self.in_collision_recovery:
            if now >= self.recovery_end_time:
                self.in_collision_recovery = False
                self.target_linear = 0.0
                self.target_angular = 0.0
                self.current_state = 'DUNG YEN'

        # Auto-Stop khi nhả phím (Deadman switch)
        elif self.deadman_mode and (now - self.last_key_time > self.key_timeout):
            if abs(self.target_linear) > 0.01 or abs(self.target_angular) > 0.01:
                self.target_linear = 0.0
                self.target_angular = 0.0
                self.current_state = 'DUNG YEN'

        msg = Twist()
        msg.linear.x = self.target_linear
        msg.angular.z = self.target_angular
        self.pub_cmd_vel.publish(msg)
        self.pub_diff.publish(msg)

    def stop_robot(self):
        self.target_linear = 0.0
        self.target_angular = 0.0
        stop_msg = Twist()
        self.pub_cmd_vel.publish(stop_msg)
        self.pub_diff.publish(stop_msg)


def get_key(settings, timeout=0.04):
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    if rlist:
        ch = sys.stdin.read(1)
        # Bat phim mui ten (Escape sequences \x1b[A, \x1b[B, ...)
        if ch == '\x1b':
            rlist2, _, _ = select.select([sys.stdin], [], [], 0.05)
            if rlist2:
                seq = sys.stdin.read(2)
                if seq == '[A': return 'KEY_UP'
                elif seq == '[B': return 'KEY_DOWN'
                elif seq == '[C': return 'KEY_RIGHT'
                elif seq == '[D': return 'KEY_LEFT'
        return ch
    return None


def main(args=None):
    rclpy.init(args=args)
    node = TeleopKeyboardNode()

    # Lưu thiết lập terminal
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())

    print(BANNER)
    print(f"-> MUC TOC DO KHOI TAO: {node.linear_speed:.2f} m/s (x2) | Xoay: {node.angular_speed:.2f} rad/s")
    print(f"-> CHE DO PHANH: Auto-Stop khi tha tay = {'BAT (An toan)' if node.deadman_mode else 'TAT (Cruise)'}")
    print("San sang! Nhan va giu phim di chuyen (W/A/S/D, Mui Ten hoac I/J/K/L)...\n")

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.01)
            key = get_key(old_settings, timeout=0.04)
            if key is not None:
                if key == '\x03':  # Ctrl+C
                    break
                elif key in MOVE_BINDINGS:
                    lin_f, ang_f, label = MOVE_BINDINGS[key]
                    node.set_motion(lin_f, ang_f, label)
                    sys.stdout.write(f"\r[{label:<18}] V: {node.target_linear:+.2f} m/s | W: {node.target_angular:+.2f} rad/s   ")
                    sys.stdout.flush()
                elif key == '1':
                    node.set_preset_speed(0.46, 1.80, 'MUC 1 (0.46 m/s)')
                    sys.stdout.write(f"\r[CHON MUC 1 (1x)]   Lin: {node.linear_speed:.2f} m/s | Ang: {node.angular_speed:.2f} rad/s   ")
                    sys.stdout.flush()
                elif key == '2':
                    node.set_preset_speed(0.92, 2.20, 'MUC 2 (0.92 m/s)')
                    sys.stdout.write(f"\r[CHON MUC 2 (2x)]   Lin: {node.linear_speed:.2f} m/s | Ang: {node.angular_speed:.2f} rad/s   ")
                    sys.stdout.flush()
                elif key == '3':
                    node.set_preset_speed(1.15, 2.40, 'MUC 3 (1.15 m/s)')
                    sys.stdout.write(f"\r[CHON MUC 3 (2.5x)] Lin: {node.linear_speed:.2f} m/s | Ang: {node.angular_speed:.2f} rad/s   ")
                    sys.stdout.flush()
                elif key in ('p', 'P'):
                    state = node.toggle_deadman()
                    mode_str = "Auto-Stop (Nha tay tu dung)" if state else "Cruise (Giu ga tu dong)"
                    sys.stdout.write(f"\r[CHE DO LAI]        {mode_str:<32}   ")
                    sys.stdout.flush()
                elif key in ('q', 'Q'):
                    node.adjust_speed(1.1, 1.0)
                    sys.stdout.write(f"\r[TANG TOC DOI]      Lin: {node.linear_speed:.2f} m/s | Ang: {node.angular_speed:.2f} rad/s   ")
                    sys.stdout.flush()
                elif key in ('z', 'Z'):
                    node.adjust_speed(0.9, 1.0)
                    sys.stdout.write(f"\r[GIAM TOC DOI]      Lin: {node.linear_speed:.2f} m/s | Ang: {node.angular_speed:.2f} rad/s   ")
                    sys.stdout.flush()
                elif key in ('e', 'E'):
                    node.adjust_speed(1.0, 1.1)
                    sys.stdout.write(f"\r[TANG TOC XOAY]     Lin: {node.linear_speed:.2f} m/s | Ang: {node.angular_speed:.2f} rad/s   ")
                    sys.stdout.flush()
                elif key in ('c', 'C'):
                    node.adjust_speed(1.0, 0.9)
                    sys.stdout.write(f"\r[GIAM TOC XOAY]     Lin: {node.linear_speed:.2f} m/s | Ang: {node.angular_speed:.2f} rad/s   ")
                    sys.stdout.flush()
                else:
                    # Neu la phim Enter hoac ky tu la khac thi bo qua, khong phanh gap
                    pass

    except Exception as e:
        print(f"\nLoi: {e}")

    finally:
        # Khoi phuc thiet lap ban phim
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        node.stop_robot()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        print("\nDa dung node teleop va khoi phuc ban phim thanh cong.")


if __name__ == '__main__':
    main()
