import csv
import math
import os
import sys
import time

import rclpy
import yaml
from rclpy.node import Node
from gazebo_msgs.msg import ModelStates
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from rclpy.action import ActionClient
from rclpy.task import Future
from hunav_msgs.msg import Agents
from ament_index_python.packages import get_package_share_directory

from ethical_testing.config.waypoints import waypoints


class EthicalNavClient(Node):
    def __init__(self):
        super().__init__('ethical_navigation_client')
        self.action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.goal_pub = self.create_publisher(PoseStamped, 'current_goal_pose', 1)
        self._get_result_future = None
        self._result_handled = False
        self._goal_handle = None
        self.timeout_flag = False
        self._nav_timeout_timer = None
        self._cancel_watchdog_timer = None
        self.last_log_time = None
        self.log_time_period = 0.5
        self.robot_radius = 0.35
        self.worker_radius = 0.4
        self.failure_reason = ""

        self.robot_odom_subscription = self.create_subscription(
            Odometry,
            '/mobile_base_controller/odom',
            self.robot_odom_callback,
            10)

        self.robot_imu_subscription = self.create_subscription(
            Imu,
            '/imu_sensor_broadcaster/imu',
            self.robot_imu_callback,
            10)

        self.human_states_subscription = self.create_subscription(
            Agents,
            '/human_states',
            self.human_states_callback,
            10)

        self.model1_name = 'worker1'
        self.model2_name = 'worker2'
        self.odom_data_ready = False
        self.imu_data_ready = False
        self.model_states_ready = False

        self.declare_parameter('number', 0)
        self.number = self.get_parameter('number').get_parameter_value().integer_value
        self.declare_parameter('episode', 0)
        self.episode = self.get_parameter('episode').get_parameter_value().integer_value
        self.declare_parameter('route', 'route_1')
        self.route = self.get_parameter('route').get_parameter_value().string_value
        self.declare_parameter('req', 'privacy')
        self.req = self.get_parameter('req').get_parameter_value().string_value

        output_folder = os.path.expanduser("~/yelyzaveta/hunav_and_omni_base_ws/ethical_output")
        os.makedirs(output_folder, exist_ok=True)

        self.out_folder = os.path.join(output_folder, self.req, self.route, str(self.episode))
        os.makedirs(self.out_folder, exist_ok=True)

        from ethical_testing.ethical_hunav import route_start_end
        self.x_goal = route_start_end[self.route]["end"]["x"]
        self.y_goal = route_start_end[self.route]["end"]["y"]
        self.yaw_goal = route_start_end[self.route]["end"]["yaw"]
        self.timeout_sec = route_start_end[self.route]["timeout"]

        header = [
            'timestamp', 'robot_x', 'robot_y', 'robot_wp',
            'robot_orientation_z', 'robot_orientation_w',
            'robot_linear_velocity_x', 'robot_linear_velocity_y', 'robot_speed',
            'robot_angular_velocity_z',
            'robot_linear_acceleration_x', 'robot_linear_acceleration_y', 'robot_acceleration',

            'worker1_x', 'worker1_y', 'worker1_wp',
            'worker1_orientation_z', 'worker1_orientation_w',
            'worker1_linear_velocity_x', 'worker1_linear_velocity_y', 'worker1_speed',
            'worker1_angular_velocity_z',

            'worker2_x', 'worker2_y', 'worker2_wp',
            'worker2_orientation_z', 'worker2_orientation_w',
            'worker2_linear_velocity_x', 'worker2_linear_velocity_y', 'worker2_speed',
            'worker2_angular_velocity_z',

            'time_to_reach_goal', 'path_length', 'cumulative_heading_changes', 'avg_distance_to_closest_person',
            'minimum_distance_to_people', 'completed', 'minimum_distance_to_target', 'final_distance_to_target',
            'robot_on_person_collision', 'person_on_robot_collision', 'time_not_moving',
            'avg_robot_linear_speed', 'avg_robot_angular_speed', 'avg_robot_acceleration', 'avg_robot_jerk',
            'avg_pedestrian_velocity', 'avg_closest_pedestrian_velocity',

            'privacy_violated', 'privacy_violation_duration', 'privacy_violation_count'
        ]

        self.metrics_lists = {}
        self.metrics_to_compute = {}

        self.timestamp_list = []
        self.robot_x_dict = {}
        self.robot_y_dict = {}
        self.robot_wp_dict = {}
        self.robot_orientation_z_dict = {}
        self.robot_orientation_w_dict = {}
        self.robot_linear_velocity_x_dict = {}
        self.robot_linear_velocity_y_dict = {}
        self.robot_speed_dict = {}
        self.robot_angular_velocity_z_dict = {}
        self.robot_linear_acceleration_x_dict = {}
        self.robot_linear_acceleration_y_dict = {}
        self.robot_acceleration_dict = {}
        self.worker1_x_dict = {}
        self.worker1_y_dict = {}
        self.worker1_wp_dict = {}
        self.worker1_orientation_z_dict = {}
        self.worker1_orientation_w_dict = {}
        self.worker1_linear_velocity_x_dict = {}
        self.worker1_linear_velocity_y_dict = {}
        self.worker1_speed_dict = {}
        self.worker1_angular_velocity_z_dict = {}
        self.worker2_x_dict = {}
        self.worker2_y_dict = {}
        self.worker2_wp_dict = {}
        self.worker2_orientation_z_dict = {}
        self.worker2_orientation_w_dict = {}
        self.worker2_linear_velocity_x_dict = {}
        self.worker2_linear_velocity_y_dict = {}
        self.worker2_speed_dict = {}
        self.worker2_angular_velocity_z_dict = {}
        self.time_to_reach_goal = 0.0
        self.inside_restricted_dict = {}
        self.area_name_dict = {}
        self.completed_list = []
        self.restricted_areas = self.load_restricted_areas()
        self.run_succeeded = False

    def load_restricted_areas(self):
        try:
            pkg_share = get_package_share_directory("ethical_testing")
            yaml_path = os.path.join(pkg_share, "config", "restricted_areas.yaml")

            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f) or {}

            areas = []
            for item in data.get("restricted_areas", []):
                name = item.get("name", "unknown")
                poly = item.get("polygon", [])

                if not isinstance(poly, list) or len(poly) < 3:
                    self.get_logger().warn(
                        f"Restricted area '{name}' has invalid polygon; skipping."
                    )
                    continue

                ok = True
                for p in poly:
                    if not (isinstance(p, list) and len(p) == 2):
                        ok = False
                        break
                    try:
                        float(p[0])
                        float(p[1])
                    except Exception:
                        ok = False
                        break

                if not ok:
                    self.get_logger().warn(
                        f"Restricted area '{name}' polygon points invalid; skipping."
                    )
                    continue

                areas.append({"name": name, "polygon": poly})

            self.get_logger().info(f"Loaded {len(areas)} restricted areas from YAML.")
            self.get_logger().info(f"Loaded araes: {areas}")
            return areas

        except FileNotFoundError:
            self.get_logger().warn("restricted_areas.yaml not found. No restricted areas loaded.")
            return []

        except Exception as e:
            self.get_logger().error(f"Failed to load restricted_areas.yaml: {e}")
            return []


    def robot_odom_callback(self, msg):
        self.robot_x = msg.pose.pose.position.x
        self.robot_y = msg.pose.pose.position.y
        self.robot_orientation_z = msg.pose.pose.orientation.z
        self.robot_orientation_w = msg.pose.pose.orientation.w
        self.robot_linear_velocity_x = msg.twist.twist.linear.x
        self.robot_linear_velocity_y = msg.twist.twist.linear.y
        self.robot_speed = math.sqrt(self.robot_linear_velocity_x ** 2 + self.robot_linear_velocity_y ** 2)
        self.robot_angular_velocity_z = msg.twist.twist.angular.z

        variables = [
            self.robot_x, self.robot_y, self.robot_orientation_z, self.robot_orientation_w,
            self.robot_linear_velocity_x, self.robot_linear_velocity_y,
            self.robot_speed, self.robot_angular_velocity_z
        ]
        self.odom_data_ready = all(v is not None for v in variables)

    def robot_imu_callback(self, msg):
        self.robot_linear_acceleration_x = msg.linear_acceleration.x
        self.robot_linear_acceleration_y = msg.linear_acceleration.y
        self.robot_acceleration = math.sqrt(self.robot_linear_acceleration_x ** 2 + self.robot_linear_acceleration_y ** 2)

        variables = [
            self.robot_linear_acceleration_x,
            self.robot_linear_acceleration_y,
            self.robot_acceleration
        ]
        self.imu_data_ready = all(v is not None for v in variables)

    def human_states_callback(self, msg):
        if len(msg.agents) < 2:
            self.model_states_ready = False
            return

        worker1 = msg.agents[0]
        self.worker1_x = worker1.position.position.x
        self.worker1_y = worker1.position.position.y
        self.worker1_orientation_z = worker1.position.orientation.z
        self.worker1_orientation_w = worker1.position.orientation.w
        self.worker1_linear_velocity_x = worker1.velocity.linear.x
        self.worker1_linear_velocity_y = worker1.velocity.linear.y
        self.worker1_speed = math.sqrt(self.worker1_linear_velocity_x ** 2 + self.worker1_linear_velocity_y ** 2)
        self.worker1_angular_velocity_z = worker1.velocity.angular.z

        worker2 = msg.agents[1]
        self.worker2_x = worker2.position.position.x
        self.worker2_y = worker2.position.position.y
        self.worker2_orientation_z = worker2.position.orientation.z
        self.worker2_orientation_w = worker2.position.orientation.w
        self.worker2_linear_velocity_x = worker2.velocity.linear.x
        self.worker2_linear_velocity_y = worker2.velocity.linear.y
        self.worker2_speed = math.sqrt(self.worker2_linear_velocity_x ** 2 + self.worker2_linear_velocity_y ** 2)
        self.worker2_angular_velocity_z = worker2.velocity.angular.z

        variables = [
            self.worker1_x, self.worker1_y,
            self.worker1_orientation_z, self.worker1_orientation_w,
            self.worker1_linear_velocity_x, self.worker1_linear_velocity_y,
            self.worker1_speed, self.worker1_angular_velocity_z,
            self.worker2_x, self.worker2_y,
            self.worker2_orientation_z, self.worker2_orientation_w,
            self.worker2_linear_velocity_x, self.worker2_linear_velocity_y,
            self.worker2_speed, self.worker2_angular_velocity_z
        ]
        self.model_states_ready = all(v is not None for v in variables)

    def send_goal(self):
        goal_msg = NavigateToPose.Goal()

        pose_stamped = PoseStamped()
        pose_stamped.header.frame_id = "map"
        pose_stamped.header.stamp = self.get_clock().now().to_msg()
        pose_stamped.pose.position.x = self.x_goal
        pose_stamped.pose.position.y = self.y_goal
        pose_stamped.pose.orientation.z = math.sin(self.yaw_goal / 2.0)
        pose_stamped.pose.orientation.w = math.cos(self.yaw_goal / 2.0)

        goal_msg.pose = pose_stamped

        if not self.wait_for_two_humans(timeout_sec=15.0):
            self.get_logger().error("No 2 humans received on /human_states within timeout. Aborting run.")
            self.failure_reason = "NO_HUMANS"
            self.run_succeeded = False
            self._result_handled = True
            return False


        self.goal_pub.publish(pose_stamped)
        self.get_logger().info('Waiting for action server...')
        if not self.action_client.wait_for_server(timeout_sec=20.0):
            self.get_logger().error("NavigateToPose action server not available within timeout. Aborting run.")
            self.run_succeeded = False
            self._result_handled = True
            return False



        self.get_logger().info('Sending goal request...')
        send_goal_future = self.action_client.send_goal_async(goal_msg, feedback_callback=self.feedback_callback)
        send_goal_future.add_done_callback(self.goal_response_callback)

        self.timeout_flag = False
        if self._nav_timeout_timer is not None:
            self._nav_timeout_timer.cancel()
            self._nav_timeout_timer = None
        if self._cancel_watchdog_timer is not None:
            self._cancel_watchdog_timer.cancel()
            self._cancel_watchdog_timer = None

        self._nav_timeout_timer = self.create_timer(self.timeout_sec, self.nav_timeout_handler)

        return True

    def wait_for_two_humans(self, timeout_sec=10.0, poll_sec=0.1):
        self.get_logger().info("Waiting for 2 humans on /human_states...")
        deadline = time.time() + timeout_sec
        while rclpy.ok() and time.time() < deadline:
            if self.model_states_ready:
                return True
            rclpy.spin_once(self, timeout_sec=poll_sec)
        return False

    def feedback_callback(self, feedback_msg):
        if self.odom_data_ready and self.imu_data_ready and self.model_states_ready:
            if self.last_log_time is None:
                self.last_log_time = self.get_clock().now()
                self.timestamp_list.append(self.get_seconds(self.last_log_time, self.last_log_time))
                self.obtain_log_data(self.timestamp_list[-1])
            else:
                current_time = self.get_clock().now()
                secs = self.get_seconds(self.last_log_time, current_time)
                if secs >= self.log_time_period:
                    feedback = feedback_msg.feedback
                    self.get_logger().info(f'Received feedback: {feedback.distance_remaining:.2f} meters remaining')
                    self.time_to_reach_goal += secs
                    self.timestamp_list.append(secs + self.timestamp_list[-1])
                    self.obtain_log_data(self.timestamp_list[-1])
                    self.last_log_time = current_time

    def goal_response_callback(self, future):
        try:
            goal_handle = future.result()
            if not goal_handle.accepted:
                self.get_logger().info('Goal rejected')
                rclpy.shutdown()
                return
            self.get_logger().info('Goal accepted')
            self._goal_handle = goal_handle
            self._get_result_future = goal_handle.get_result_async()
            self._get_result_future.add_done_callback(self.get_result_callback)
        except Exception as e:
            self.get_logger().error(f"Exception in goal_response_callback: {e}")

    def nav_timeout_handler(self):
        if self._nav_timeout_timer is not None:
            self._nav_timeout_timer.cancel()
            self._nav_timeout_timer = None

        if self.timeout_flag:
            return  

        self.get_logger().warn("Navigation timeout! Canceling goal...")
        self.timeout_flag = True

        if self._cancel_watchdog_timer is not None:
            self._cancel_watchdog_timer.cancel()
        self._cancel_watchdog_timer = self.create_timer(5.0, self.force_finish_after_cancel)

        if self._goal_handle is not None:
            future = self._goal_handle.cancel_goal_async()
            future.add_done_callback(self.cancel_done_callback)
        else:
            self.force_finish_after_cancel()

    def cancel_done_callback(self, future):
        self.get_logger().info("Goal cancel request completed.")

    def force_finish_after_cancel(self):
        if self._cancel_watchdog_timer is not None:
            self._cancel_watchdog_timer.cancel()
            self._cancel_watchdog_timer = None

        if self._result_handled:
            return

        self.get_logger().warn("Cancel watchdog fired: finishing run without Nav2 result.")
        self.run_succeeded = False

        try:
            if len(self.timestamp_list) >= 2:
                self.compute_metrics(False)
            else:
                self.get_logger().warn("Not enough data to compute metrics; skipping metrics storage.")
        except Exception as e:
            self.get_logger().error(f"Failed to compute metrics on cancel watchdog: {e}")
            self.run_succeeded = False

        self._result_handled = True

    def get_result_callback(self, future):
        try:
            current_time = self.get_clock().now()
            secs = self.get_seconds(self.last_log_time, current_time)
            self.time_to_reach_goal += secs
            self.timestamp_list.append(secs + self.timestamp_list[-1])
            self.obtain_log_data(self.timestamp_list[-1])

            if self.timeout_flag:
                self.get_logger().warn("Timeout! Navigation canceled!")
                self.compute_metrics(False)
                self.run_succeeded = False
            else:
                self.get_logger().info("Navigation succeeded!")
                if not self.humans_motion_valid(min_disp=0.20):
                    self.get_logger().error(
                        f"Robot reached goal but run invalid ({self.failure_reason}). Marking as failed for retry."
                    )
                    self.run_succeeded = False
                    if len(self.timestamp_list) >= 2:
                        self.compute_metrics(False)
                    else:
                        self.get_logger().warn("Not enough data to compute metrics; skipping metrics storage.")
                else:
                    self.run_succeeded = True
                    self.compute_metrics(True)


        except Exception as e:
            self.get_logger().error(f'Failed to get navigation result: {e}')
            self.compute_metrics(False)
            self.run_succeeded = False
        finally:
            self._result_handled = True
            if self._cancel_watchdog_timer is not None:
                self._cancel_watchdog_timer.cancel()
                self._cancel_watchdog_timer = None
            if self._nav_timeout_timer is not None:
                self._nav_timeout_timer.cancel()
                self._nav_timeout_timer = None
    
    def humans_motion_valid(self, min_disp=0.20):
        if len(self.timestamp_list) < 2:
            self.failure_reason = "NO_HUMAN_LOG"
            return False

        t0 = self.timestamp_list[0]
        tN = self.timestamp_list[-1]

        if t0 not in self.worker1_x_dict or tN not in self.worker1_x_dict:
            self.failure_reason = "NO_HUMAN_LOG"
            return False
        if t0 not in self.worker2_x_dict or tN not in self.worker2_x_dict:
            self.failure_reason = "NO_HUMAN_LOG"
            return False

        d1 = math.hypot(self.worker1_x_dict[tN] - self.worker1_x_dict[t0],
                        self.worker1_y_dict[tN] - self.worker1_y_dict[t0])
        d2 = math.hypot(self.worker2_x_dict[tN] - self.worker2_x_dict[t0],
                        self.worker2_y_dict[tN] - self.worker2_y_dict[t0])

        if d1 < min_disp and d2 < min_disp:
            self.failure_reason = "HUMANS_STALE"
            return False

        return True

    def compute_metrics(self, completed):
        if len(self.timestamp_list) == 0:
            self.get_logger().warn("compute_metrics called with empty timestamp_list; storing minimal metrics.")
            self.metrics_lists = {'timestamp': []}

            self.metrics_to_compute['time_to_reach_goal'] = 0.0
            self.metrics_to_compute['path_length'] = 0.0
            self.metrics_to_compute['cumulative_heading_changes'] = 0.0
            self.metrics_to_compute['avg_distance_to_closest_person'] = 0.0
            self.metrics_to_compute['minimum_distance_to_people'] = 0.0
            self.metrics_to_compute['completed'] = False
            self.metrics_to_compute['minimum_distance_to_target'] = 0.0
            self.metrics_to_compute['final_distance_to_target'] = 0.0
            self.metrics_to_compute['robot_on_person_collision'] = 0
            self.metrics_to_compute['person_on_robot_collision'] = 0
            self.metrics_to_compute['time_not_moving'] = 0.0
            self.metrics_to_compute['avg_robot_linear_speed'] = 0.0
            self.metrics_to_compute['avg_robot_angular_speed'] = 0.0
            self.metrics_to_compute['avg_robot_acceleration'] = 0.0
            self.metrics_to_compute['avg_robot_jerk'] = 0.0
            self.metrics_to_compute['avg_pedestrian_velocity'] = 0.0
            self.metrics_to_compute['avg_closest_pedestrian_velocity'] = 0.0
            self.metrics_to_compute['privacy_violated'] = 0
            self.metrics_to_compute['privacy_violation_duration'] = 0.0
            self.metrics_to_compute['privacy_violation_count'] = 0

            self.store_metrics()
            return

        for i in range(len(self.timestamp_list)):
            if i == len(self.timestamp_list) - 1:
                self.completed_list.append(completed)
            else:
                self.completed_list.append(False)

        self.metrics_lists['timestamp'] = self.timestamp_list
        self.metrics_lists['robot_x'] = list(self.robot_x_dict.values())
        self.metrics_lists['robot_y'] = list(self.robot_y_dict.values())
        self.metrics_lists['robot_wp'] = list(self.robot_wp_dict.values())
        self.metrics_lists['robot_orientation_z'] = list(self.robot_orientation_z_dict.values())
        self.metrics_lists['robot_orientation_w'] = list(self.robot_orientation_w_dict.values())
        self.metrics_lists['robot_linear_velocity_x'] = list(self.robot_linear_velocity_x_dict.values())
        self.metrics_lists['robot_linear_velocity_y'] = list(self.robot_linear_velocity_y_dict.values())
        self.metrics_lists['robot_speed'] = list(self.robot_speed_dict.values())
        self.metrics_lists['robot_angular_velocity_z'] = list(self.robot_angular_velocity_z_dict.values())
        self.metrics_lists['robot_linear_acceleration_x'] = list(self.robot_linear_acceleration_x_dict.values())
        self.metrics_lists['robot_linear_acceleration_y'] = list(self.robot_linear_acceleration_y_dict.values())
        self.metrics_lists['robot_acceleration'] = list(self.robot_acceleration_dict.values())
        self.metrics_lists['worker1_x'] = list(self.worker1_x_dict.values())
        self.metrics_lists['worker1_y'] = list(self.worker1_y_dict.values())
        self.metrics_lists['worker1_wp'] = list(self.worker1_wp_dict.values())
        self.metrics_lists['worker1_orientation_z'] = list(self.worker1_orientation_z_dict.values())
        self.metrics_lists['worker1_orientation_w'] = list(self.worker1_orientation_w_dict.values())
        self.metrics_lists['worker1_linear_velocity_x'] = list(self.worker1_linear_velocity_x_dict.values())
        self.metrics_lists['worker1_linear_velocity_y'] = list(self.worker1_linear_velocity_y_dict.values())
        self.metrics_lists['worker1_speed'] = list(self.worker1_speed_dict.values())
        self.metrics_lists['worker1_angular_velocity_z'] = list(self.worker1_angular_velocity_z_dict.values())
        self.metrics_lists['worker2_x'] = list(self.worker2_x_dict.values())
        self.metrics_lists['worker2_y'] = list(self.worker2_y_dict.values())
        self.metrics_lists['worker2_wp'] = list(self.worker2_wp_dict.values())
        self.metrics_lists['worker2_orientation_z'] = list(self.worker2_orientation_z_dict.values())
        self.metrics_lists['worker2_orientation_w'] = list(self.worker2_orientation_w_dict.values())
        self.metrics_lists['worker2_linear_velocity_x'] = list(self.worker2_linear_velocity_x_dict.values())
        self.metrics_lists['worker2_linear_velocity_y'] = list(self.worker2_linear_velocity_y_dict.values())
        self.metrics_lists['worker2_speed'] = list(self.worker2_speed_dict.values())
        self.metrics_lists['worker2_angular_velocity_z'] = list(self.worker2_angular_velocity_z_dict.values())

        self.metrics_to_compute['time_to_reach_goal'] = self.time_to_reach_goal
        self.metrics_to_compute['path_length'] = self.robot_path_length()
        metric = self.cumulative_heading_changes()
        self.metrics_to_compute['cumulative_heading_changes'] = metric[0]
        self.metrics_lists['cumulative_heading_changes'] = metric[1]
        metric = self.avg_distance_to_closest_person()
        self.metrics_to_compute['avg_distance_to_closest_person'] = metric[0]
        self.metrics_lists['distance_to_closest_person'] = metric[1]
        self.metrics_to_compute['minimum_distance_to_people'] = self.minimum_distance_to_people()
        self.metrics_to_compute['completed'] = self.completed_list[-1]
        self.metrics_lists['completed'] = self.completed_list
        self.metrics_to_compute['minimum_distance_to_target'] = self.minimum_distance_to_target()
        self.metrics_to_compute['final_distance_to_target'] = self.final_distance_to_target()
        metric = self.robot_on_person_collision()
        self.metrics_to_compute['robot_on_person_collision'] = metric[0]
        self.metrics_lists['robot_on_person_collision'] = metric[1]
        metric = self.person_on_robot_collision()
        self.metrics_to_compute['person_on_robot_collision'] = metric[0]
        self.metrics_lists['person_on_robot_collision'] = metric[1]
        metric = self.time_not_moving()
        self.metrics_to_compute['time_not_moving'] = metric[0]
        self.metrics_lists['time_not_moving'] = metric[1]
        metric = self.avg_robot_linear_speed()
        self.metrics_to_compute['avg_robot_linear_speed'] = metric[0]
        self.metrics_lists['robot_linear_speed'] = metric[1]
        metric = self.avg_robot_angular_speed()
        self.metrics_to_compute['avg_robot_angular_speed'] = metric[0]
        self.metrics_lists['robot_angular_speed'] = metric[1]
        metric = self.avg_robot_acceleration()
        self.metrics_to_compute['avg_robot_acceleration'] = metric[0]
        self.metrics_lists['robot_acceleration'] = metric[1]
        metric = self.avg_robot_jerk()
        self.metrics_to_compute['avg_robot_jerk'] = metric[0]
        self.metrics_lists['robot_jerk'] = metric[1]
        metric = self.avg_pedestrian_velocity()
        self.metrics_to_compute['avg_pedestrian_velocity'] = metric[0]
        self.metrics_lists['avg_pedestrian_velocity'] = metric[1]
        metric = self.avg_closest_pedestrian_velocity()
        self.metrics_to_compute['avg_closest_pedestrian_velocity'] = metric[0]
        self.metrics_lists['avg_closest_pedestrian_velocity'] = metric[1]
        metric = self.privacy_violated()
        self.metrics_to_compute['privacy_violated'] = metric[0]
        self.metrics_lists['privacy_violated'] = metric[1]
        metric = self.privacy_violation_duration()
        self.metrics_to_compute['privacy_violation_duration'] = metric[0]
        self.metrics_lists['privacy_violation_duration'] = metric[1]
        metric = self.privacy_violation_count()
        self.metrics_to_compute['privacy_violation_count'] = metric[0]
        self.metrics_lists['privacy_violation_count'] = metric[1]
        metric = self.restricted_area_name()
        self.metrics_to_compute['restricted_area_count'] = metric[0]
        self.metrics_lists['restricted_area_name'] = metric[1]


        self.store_metrics()

    def store_metrics(self):
        base_filename = f"{self.out_folder}/log"
        metrics_file = base_filename + '.csv'
        steps_file = base_filename + f'_{self.number}.csv'
        file_exists = os.path.exists(metrics_file)

        with open(metrics_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(['experiment_tag'] + list(self.metrics_to_compute.keys()))
            row = [f"{self.episode}_{self.number}"] + list(self.metrics_to_compute.values())
            writer.writerow(row)

        with open(steps_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            headers = list(self.metrics_lists.keys())
            writer.writerow(headers)
            num_rows = len(self.metrics_lists['timestamp'])
            for i in range(num_rows):
                row = []
                for m in headers:
                    metric_list = self.metrics_lists.get(m, [])
                    if len(metric_list) != 0:
                        val = metric_list[i]
                        row.append(val)
                    else:
                        row.append(None)
                writer.writerow(row)

    def get_seconds(self, t1, t2):
        dur = (t2 - t1).to_msg()
        secs = float(dur.sec + dur.nanosec / 1e9)
        return secs

    def obtain_log_data(self, timestamp):
        self.robot_x_dict[timestamp] = self.robot_x
        self.robot_y_dict[timestamp] = self.robot_y
        robot_wp = min(
            waypoints,
            key=lambda name: math.hypot(waypoints[name]['x'] - self.robot_x,
                                        waypoints[name]['y'] - self.robot_y)
        )
        self.robot_wp_dict[timestamp] = robot_wp
        self.robot_orientation_z_dict[timestamp] = self.robot_orientation_z
        self.robot_orientation_w_dict[timestamp] = self.robot_orientation_w
        self.robot_linear_velocity_x_dict[timestamp] = self.robot_linear_velocity_x
        self.robot_linear_velocity_y_dict[timestamp] = self.robot_linear_velocity_y
        self.robot_speed_dict[timestamp] = self.robot_speed
        self.robot_angular_velocity_z_dict[timestamp] = self.robot_angular_velocity_z
        self.robot_linear_acceleration_x_dict[timestamp] = self.robot_linear_acceleration_x
        self.robot_linear_acceleration_y_dict[timestamp] = self.robot_linear_acceleration_y
        self.robot_acceleration_dict[timestamp] = self.robot_acceleration
        self.worker1_x_dict[timestamp] = self.worker1_x
        self.worker1_y_dict[timestamp] = self.worker1_y
        worker1_wp = min(
            waypoints,
            key=lambda name: math.hypot(waypoints[name]['x'] - self.worker1_x,
                                        waypoints[name]['y'] - self.worker1_y)
        )
        self.worker1_wp_dict[timestamp] = worker1_wp
        self.worker1_orientation_z_dict[timestamp] = self.worker1_orientation_z
        self.worker1_orientation_w_dict[timestamp] = self.worker1_orientation_w
        self.worker1_linear_velocity_x_dict[timestamp] = self.worker1_linear_velocity_x
        self.worker1_linear_velocity_y_dict[timestamp] = self.worker1_linear_velocity_y
        self.worker1_speed_dict[timestamp] = self.worker1_speed
        self.worker1_angular_velocity_z_dict[timestamp] = self.worker1_angular_velocity_z
        self.worker2_x_dict[timestamp] = self.worker2_x
        self.worker2_y_dict[timestamp] = self.worker2_y
        worker2_wp = min(
            waypoints,
            key=lambda name: math.hypot(waypoints[name]['x'] - self.worker2_x,
                                        waypoints[name]['y'] - self.worker2_y)
        )
        self.worker2_wp_dict[timestamp] = worker2_wp
        self.worker2_orientation_z_dict[timestamp] = self.worker2_orientation_z
        self.worker2_orientation_w_dict[timestamp] = self.worker2_orientation_w
        self.worker2_linear_velocity_x_dict[timestamp] = self.worker2_linear_velocity_x
        self.worker2_linear_velocity_y_dict[timestamp] = self.worker2_linear_velocity_y
        self.worker2_speed_dict[timestamp] = self.worker2_speed
        self.worker2_angular_velocity_z_dict[timestamp] = self.worker2_angular_velocity_z

        inside, area_name = self.check_privacy_violation(self.robot_x, self.robot_y)

        self.get_logger().info(
            f"privacy sample: t={timestamp:.2f}, x={self.robot_x:.3f}, y={self.robot_y:.3f}, inside={inside}, area={area_name}"
        )

        if inside:
            self.get_logger().info(
                f"Privacy hit at t={timestamp:.2f}: area={area_name}, x={self.robot_x:.3f}, y={self.robot_y:.3f}"
            )

        self.inside_restricted_dict[timestamp] = int(inside)
        self.area_name_dict[timestamp] = area_name

    def point_in_polygon(self, x, y, polygon):
        inside = False
        n = len(polygon)
        if n < 3:
            return False

        x1, y1 = polygon[0]
        for i in range(1, n + 1):
            x2, y2 = polygon[i % n]
            if ((y1 > y) != (y2 > y)):
                x_intersect = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1
                if x < x_intersect:
                    inside = not inside
            x1, y1 = x2, y2

        return inside

    def check_privacy_violation(self, x, y):
        x = float(x)
        y = float(y)

        for area in self.restricted_areas:
            name = str(area["name"])
            polygon = area["polygon"]
            hit = self.point_in_polygon(x, y, polygon)

            self.get_logger().info(
                f"privacy area check: area={name}, x={x:.3f}, y={y:.3f}, hit={hit}, polygon={polygon}"
            )

            if hit:
                return True, name

        return False, ""

    def euclidean_distance(self, x1, x2, y1, y2):
        return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

    def robot_path_length(self):
        path_length = 0.0
        for i in range(len(self.timestamp_list) - 1):
            path_length += self.euclidean_distance(self.robot_x_dict[self.timestamp_list[i]], self.robot_x_dict[self.timestamp_list[i+1]],
                                                   self.robot_y_dict[self.timestamp_list[i]], self.robot_y_dict[self.timestamp_list[i+1]])
        return path_length

    def quaternion_to_yaw(self, z, w):
        yaw = math.atan2(2.0 * w * z, 1.0 - 2.0 * z * z)
        return yaw

    def normalize_angle(self, angle):
        return (angle + math.pi) % (2 * math.pi) - math.pi

    def cumulative_heading_changes(self):
        chc_list = [0.0]
        chc = 0.0
        for i in range(len(self.timestamp_list) - 1):
            yaw_1 = self.quaternion_to_yaw(self.robot_orientation_z_dict[self.timestamp_list[i+1]], self.robot_orientation_w_dict[self.timestamp_list[i+1]])
            yaw_0 = self.quaternion_to_yaw(self.robot_orientation_z_dict[self.timestamp_list[i]], self.robot_orientation_w_dict[self.timestamp_list[i]])
            norm = self.normalize_angle(yaw_1 - yaw_0)
            norm = abs(norm)
            chc += norm
            chc_list.append(norm)
        return [chc, chc_list]

    def avg_distance_to_closest_person(self):
        min_dist_list = []
        avg_dist = 0
        for ts in self.timestamp_list:
            d1 = self.euclidean_distance(self.robot_x_dict[ts], self.worker1_x_dict[ts],
                                         self.robot_y_dict[ts], self.worker1_y_dict[ts])
            d1 -= self.robot_radius + self.worker_radius
            d2 = self.euclidean_distance(self.robot_x_dict[ts], self.worker2_x_dict[ts],
                                         self.robot_y_dict[ts], self.worker2_y_dict[ts])
            d2 -= self.robot_radius + self.worker_radius
            min_dist = max(min(d1, d2), 0.0)
            avg_dist += min_dist
            min_dist_list.append(min_dist)
        avg_dist = avg_dist / len(self.timestamp_list)
        return [avg_dist, min_dist_list]

    def minimum_distance_to_people(self):
        distance_list = []
        for ts in self.timestamp_list:
            d1 = self.euclidean_distance(self.robot_x_dict[ts], self.worker1_x_dict[ts],
                                         self.robot_y_dict[ts], self.worker1_y_dict[ts])
            d1 -= self.robot_radius + self.worker_radius
            d1 = max(d1, 0.0)
            distance_list.append(d1)
            d2 = self.euclidean_distance(self.robot_x_dict[ts], self.worker2_x_dict[ts],
                                         self.robot_y_dict[ts], self.worker2_y_dict[ts])
            d2 -= self.robot_radius + self.worker_radius
            d2 = max(d2, 0.0)
            distance_list.append(d2)
        min_dist = min(distance_list)
        return min_dist

    def minimum_distance_to_target(self):
        min_dist = 10000
        for ts in self.timestamp_list:
            d = self.euclidean_distance(self.robot_x_dict[ts], self.x_goal,
                                        self.robot_y_dict[ts], self.y_goal)
            min_dist = min(min_dist, d)
        return min_dist

    def final_distance_to_target(self):
        d = self.euclidean_distance(self.robot_x_dict[self.timestamp_list[-1]], self.x_goal,
                                    self.robot_y_dict[self.timestamp_list[-1]], self.y_goal)
        return d if d > 0.25 else 0.0

    def obtain_angles(self, r_x, r_y, r_yaw, w_x, w_y, w_yaw):
        alpha1 = self.normalize_angle(math.atan2(r_y - w_y, r_x - w_x) - w_yaw)
        alpha2 = self.normalize_angle(math.atan2(w_y - r_y, w_x - r_x) - r_yaw)
        return alpha1, alpha2

    def robot_on_person_collision(self):
        robot_collisions = 0
        robot_coll_list = [0] * len(self.timestamp_list)

        for i, ts in enumerate(self.timestamp_list):
            r_x = self.robot_x_dict[ts]
            r_y = self.robot_y_dict[ts]
            r_yaw = self.quaternion_to_yaw(self.robot_orientation_z_dict[ts], self.robot_orientation_w_dict[ts])
            r_speed = self.robot_speed_dict[ts]
            r_angular_vel = self.robot_angular_velocity_z_dict[ts]
            robot_is_moving = (r_speed >= 0.01) or (abs(r_angular_vel) >= 0.02)
            w1_x = self.worker1_x_dict[ts]
            w1_y = self.worker1_y_dict[ts]
            w2_x = self.worker2_x_dict[ts]
            w2_y = self.worker2_y_dict[ts]

            d1 = self.euclidean_distance(r_x, w1_x, r_y, w1_y)
            d1 -= self.robot_radius + self.worker_radius
            d2 = self.euclidean_distance(r_x, w2_x, r_y, w2_y)
            d2 -= self.robot_radius + self.worker_radius

            if d1 < 0.02 and robot_is_moving:
                w1_yaw = self.quaternion_to_yaw(self.worker1_orientation_z_dict[ts], self.worker1_orientation_w_dict[ts])
                alpha1, alpha2 = self.obtain_angles(r_x, r_y, r_yaw, w1_x, w1_y, w1_yaw)
                w1_speed = self.worker1_speed_dict[ts]
                if abs(alpha1) < abs(alpha2):
                    robot_collisions += 1
                    robot_coll_list[i] = 1
                elif abs(alpha1) == abs(alpha2) and r_speed == w1_speed:
                    robot_collisions += 1
                    robot_coll_list[i] = 1

            if d2 < 0.02 and robot_is_moving:
                w2_yaw = self.quaternion_to_yaw(self.worker2_orientation_z_dict[ts], self.worker2_orientation_w_dict[ts])
                alpha1, alpha2 = self.obtain_angles(r_x, r_y, r_yaw, w2_x, w2_y, w2_yaw)
                w2_speed = self.worker2_speed_dict[ts]
                if abs(alpha1) < abs(alpha2):
                    robot_collisions += 1
                    robot_coll_list[i] = 1
                elif abs(alpha1) == abs(alpha2) and r_speed == w2_speed:
                    robot_collisions += 1
                    robot_coll_list[i] = 1

        return [robot_collisions, robot_coll_list]

    def person_on_robot_collision(self):
        person_collisions = 0
        person_coll_list = [0] * len(self.timestamp_list)

        for i, ts in enumerate(self.timestamp_list):
            r_x = self.robot_x_dict[ts]
            r_y = self.robot_y_dict[ts]
            r_yaw = self.quaternion_to_yaw(self.robot_orientation_z_dict[ts], self.robot_orientation_w_dict[ts])
            r_speed = self.robot_speed_dict[ts]
            w1_x = self.worker1_x_dict[ts]
            w1_y = self.worker1_y_dict[ts]
            w2_x = self.worker2_x_dict[ts]
            w2_y = self.worker2_y_dict[ts]

            d1 = self.euclidean_distance(r_x, w1_x, r_y, w1_y)
            d1 -= self.robot_radius + self.worker_radius
            d2 = self.euclidean_distance(r_x, w2_x, r_y, w2_y)
            d2 -= self.robot_radius + self.worker_radius

            if d1 < 0.02:
                w1_yaw = self.quaternion_to_yaw(self.worker1_orientation_z_dict[ts], self.worker1_orientation_w_dict[ts])
                alpha1, alpha2 = self.obtain_angles(r_x, r_y, r_yaw, w1_x, w1_y, w1_yaw)
                w1_speed = self.worker1_speed_dict[ts]
                if abs(alpha1) > abs(alpha2):
                    person_collisions += 1
                    person_coll_list[i] = 1
                elif abs(alpha1) == abs(alpha2) and r_speed == w1_speed:
                    person_collisions += 1
                    person_coll_list[i] = 1

            if d2 < 0.02:
                w2_yaw = self.quaternion_to_yaw(self.worker2_orientation_z_dict[ts], self.worker2_orientation_w_dict[ts])
                alpha1, alpha2 = self.obtain_angles(r_x, r_y, r_yaw, w2_x, w2_y, w2_yaw)
                w2_speed = self.worker2_speed_dict[ts]
                if abs(alpha1) > abs(alpha2):
                    person_collisions += 1
                    person_coll_list[i] = 1
                elif abs(alpha1) == abs(alpha2) and r_speed == w2_speed:
                    person_collisions += 1
                    person_coll_list[i] = 1

        return [person_collisions, person_coll_list]

    def time_not_moving(self):
        not_moving = [0] * len(self.timestamp_list)
        if len(self.timestamp_list) < 2:
            return [0.0, not_moving]
        time_step = self.time_to_reach_goal / (len(self.timestamp_list) - 1)
        count = 0
        for i, ts in enumerate(self.timestamp_list):
            if i == 0: continue
            r_speed = self.robot_speed_dict[ts]
            r_angular_vel = self.robot_angular_velocity_z_dict[ts]
            if r_speed < 0.01 and abs(r_angular_vel) < 0.02:
                count += 1
                not_moving[i] = 1
        time_stopped = time_step * count
        return [time_stopped, not_moving]

    def avg_robot_linear_speed(self):
        speed_list = []
        speed = 0
        for ts in self.timestamp_list:
            speed_list.append(self.robot_speed_dict[ts])
            speed += self.robot_speed_dict[ts]
        speed /= len(self.timestamp_list)
        return [speed, speed_list]

    def avg_robot_angular_speed(self):
        speed_list = []
        speed = 0
        for ts in self.timestamp_list:
            speed_list.append(self.robot_angular_velocity_z_dict[ts])
            speed += abs(self.robot_angular_velocity_z_dict[ts])
        speed /= len(self.timestamp_list)
        return [speed, speed_list]

    def avg_robot_acceleration(self):
        acceleration_list = []
        acceleration = 0
        for ts in self.timestamp_list:
            acceleration_list.append(self.robot_acceleration_dict[ts])
            acceleration += abs(self.robot_acceleration_dict[ts])
        acceleration /= len(self.timestamp_list)
        return [acceleration, acceleration_list]

    def avg_robot_jerk(self):
        jerk_list = [0.0]
        jerk = 0.0
        if len(self.timestamp_list) < 2:
            return [0.0, jerk_list]
        for i in range(len(self.timestamp_list) - 1):
            time1 = self.timestamp_list[i+1]
            time0 = self.timestamp_list[i]
            acc1 = self.robot_acceleration_dict[time1]
            acc0 = self.robot_acceleration_dict[time0]
            dt = time1 - time0
            if dt == 0:
                robot_jerk = 0.0
            else:
                robot_jerk = abs(acc1 - acc0) / dt
            jerk_list.append(robot_jerk)
            jerk += robot_jerk
        jerk /= len(self.timestamp_list) - 1
        return [jerk, jerk_list]

    def avg_pedestrian_velocity(self):
        speed_list = []
        speed = 0.0
        for ts in self.timestamp_list:
            w1_speed = self.worker1_speed_dict[ts]
            w2_speed = self.worker2_speed_dict[ts]
            speed += w1_speed + w2_speed
            speed_list.append((w1_speed + w2_speed) / 2)
        speed /= len(self.timestamp_list) * 2
        return [speed, speed_list]

    def avg_closest_pedestrian_velocity(self):
        speed_list = []
        speed = 0.0
        for ts in self.timestamp_list:
            d1 = self.euclidean_distance(self.robot_x_dict[ts], self.worker1_x_dict[ts],
                                         self.robot_y_dict[ts], self.worker1_y_dict[ts])
            d2 = self.euclidean_distance(self.robot_x_dict[ts], self.worker2_x_dict[ts],
                                         self.robot_y_dict[ts], self.worker2_y_dict[ts])
            w1_speed = self.worker1_speed_dict[ts]
            w2_speed = self.worker2_speed_dict[ts]
            if d1 < d2:
                sp = w1_speed
            elif d1 > d2:
                sp = w2_speed
            else:
                sp = (w1_speed + w2_speed) / 2
            speed += sp
            speed_list.append(sp)
        speed /= len(self.timestamp_list)
        return [speed, speed_list]
    
    #privacy metrics
    def inside_list(self):
      
        return [int(self.inside_restricted_dict.get(ts, 0)) for ts in self.timestamp_list]


    def area_list(self):

        return [str(self.area_name_dict.get(ts, "")) for ts in self.timestamp_list]

    def privacy_violated(self):
        inside_list = []
        violated = 0

        for ts in self.timestamp_list:
            v = int(self.inside_restricted_dict.get(ts, 0))
            inside_list.append(v)
            if v == 1:
                violated = 1

        return [violated, inside_list]

    def privacy_violation_duration(self):
        inside_list = []
        for ts in self.timestamp_list:
            inside_list.append(int(self.inside_restricted_dict.get(ts, 0)))

        if len(self.timestamp_list) < 2:
            time_step = 0.0
        else:
            time_step = self.time_to_reach_goal / (len(self.timestamp_list) - 1)

        duration_list = []
        total = 0.0
        for v in inside_list:
            contrib = float(v) * time_step
            duration_list.append(contrib)
            total += contrib

        return [total, duration_list]

    def privacy_violation_count(self):
        inside_list = []
        for ts in self.timestamp_list:
            inside_list.append(int(self.inside_restricted_dict.get(ts, 0)))

        entry_list = []
        count = 0
        prev = 0

        for v in inside_list:
            entry = 1 if (prev == 0 and v == 1) else 0
            entry_list.append(entry)
            count += entry
            prev = v

        return [count, entry_list]

    def restricted_presence(self):
        inside_list = []
        total_inside_steps = 0

        for ts in self.timestamp_list:
            v = int(self.inside_restricted_dict.get(ts, 0))
            inside_list.append(v)
            total_inside_steps += v

        return [total_inside_steps, inside_list]

    def restricted_area_name(self):
        area_list = []
        unique = set()

        for ts in self.timestamp_list:
            name = str(self.area_name_dict.get(ts, ""))
            area_list.append(name)
            if name:
                unique.add(name)

        return [len(unique), area_list]


def main():
    rclpy.init()
    nav_client = EthicalNavClient()
    if not nav_client.send_goal():
        if nav_client.failure_reason == "NO_HUMANS":
            exit_code = 2    
        else:
            exit_code = 1 

        nav_client.destroy_node()
        return exit_code

    while rclpy.ok():
        rclpy.spin_once(nav_client, timeout_sec=0.1)
        if nav_client._result_handled:
            break
    if nav_client.run_succeeded:
        exit_code = 0
    elif nav_client.failure_reason == "NO_HUMANS":
        exit_code = 2
    elif nav_client.failure_reason in ("HUMANS_STALE", "NO_HUMAN_LOG"):
        exit_code = 3
    else:
        exit_code = 1

    nav_client.destroy_node()
    rclpy.shutdown()
    return exit_code


if __name__ == '__main__':
    sys.exit(main())