#!/usr/bin/env python3
"""
Gui toa do muc tieu (Goal) cho Nav2 dieu khien TurtleBot 4 tu dong di den
"""
import sys
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose

class Nav2GoalSender(Node):
    def __init__(self, x, y, yaw=0.0):
        super().__init__('nav2_goal_sender')
        self._action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.x = x
        self.y = y
        self.yaw = yaw

    def send_goal(self):
        self.get_logger().info('Dang cho Nav2 NavigateToPose action server...')
        if not self._action_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('Nav2 action server chua san sang!')
            return False

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = float(self.x)
        goal_msg.pose.pose.position.y = float(self.y)
        goal_msg.pose.pose.position.z = 0.0
        goal_msg.pose.pose.orientation.w = 1.0

        self.get_logger().info(f'Dang gui Goal toi toa do: x={self.x}, y={self.y}')
        send_goal_future = self._action_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(self.goal_response_callback)
        return True

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal bi tu choi!')
            return
        self.get_logger().info('Goal duoc chap nhan! Robot dang di chuyen...')
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        status = future.result().status
        self.get_logger().info(f'Robot da hoan thanh hanh trinh voi status: {status}')
        rclpy.shutdown()

def main():
    rclpy.init()
    x = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    y = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    sender = Nav2GoalSender(x, y)
    if sender.send_goal():
        rclpy.spin(sender)

if __name__ == '__main__':
    main()
