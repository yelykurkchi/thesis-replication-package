import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
import math


class InitialPosePublisher(Node):
    def __init__(self):
        super().__init__('initial_pose_publisher')
        self.declare_parameter('x', 0.0)
        self.declare_parameter('y', 0.0)
        self.declare_parameter('yaw', 0.0)
        self.publisher_ = self.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
        timer_period = 5.0
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.published = False

    def timer_callback(self):
        if not self.published:
            x = self.get_parameter('x').get_parameter_value().double_value
            y = self.get_parameter('y').get_parameter_value().double_value
            yaw = self.get_parameter('yaw').get_parameter_value().double_value

            # yaw to quaternion
            qz = math.sin(yaw * 0.5)
            qw = math.cos(yaw * 0.5)

            msg = PoseWithCovarianceStamped()
            msg.header.frame_id = "map"
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.pose.pose.position.x = x
            msg.pose.pose.position.y = y
            msg.pose.pose.position.z = 0.0
            msg.pose.pose.orientation.x = 0.0
            msg.pose.pose.orientation.y = 0.0
            msg.pose.pose.orientation.z = qz
            msg.pose.pose.orientation.w = qw
            msg.pose.covariance = [
                0.25, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.25, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.25, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.06853891945200942, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.06853891945200942, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 0.06853891945200942
            ]
            self.publisher_.publish(msg)
            self.get_logger().info(f'Published initial pose to /initialpose: x={x}, y={y}, yaw={yaw}')
            self.published = True


def main(args=None):
    rclpy.init(args=args)
    node = InitialPosePublisher()
    while rclpy.ok() and not node.published:
        rclpy.spin_once(node, timeout_sec=0.1)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
