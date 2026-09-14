import csv
import os
import threading

import rclpy
from rclpy.node import Node
from hunav_evaluator import hunav_metrics

from hunav_msgs.msg import Agents
from hunav_msgs.msg import Agent
from std_srvs.srv import Trigger
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from rcl_interfaces.msg import Log
from ethical_testing.ethical_testing.ethical_hunav import output_root


class HunavEvaluatorNode(Node):

    def __init__(self):
        super().__init__("hunav_evaluator_node")

        self.agents_list = []
        self.robot_list = []
        self.agents = None
        self.robot = None
        self.robot_goal = None
        self.metrics_to_compute = {}
        self.metrics_lists = {}
        self.number_of_behaviors = 6

        # Indicate the frequency of capturing the data
        # (it must be slower than data publishing).
        # If the value is set to zero, the data is captured
        # at the same frequency than it is published.
        self.freq = self.declare_parameter('frequency', 0.0).get_parameter_value().double_value

        # base name of the result files
        self.declare_parameter('result_file', 'metrics')
        self.result_file_path = self.get_parameter('result_file').get_parameter_value().string_value

        self.declare_parameter('number', 0)
        self.number = self.get_parameter('number').get_parameter_value().integer_value
        self.declare_parameter('episode', 0)
        self.episode = self.get_parameter('episode').get_parameter_value().integer_value

        self.output_folder = f"{output_root}"
        os.makedirs(self.output_folder, exist_ok=True)

        # optionally, the data recording can be started when
        # a robot navigation goal is received
        self.declare_parameter('use_nav_goal_to_start', True)
        self.use_navgoal_to_start = self.get_parameter('use_nav_goal_to_start').get_parameter_value().bool_value

        # Read metrics
        for m in hunav_metrics.metrics.keys():
            ok = self.declare_parameter('metrics.' + m, True).get_parameter_value().bool_value
            if ok:
                self.metrics_to_compute[m] = 0.0

        self.get_logger().info("Hunav evaluator:")
        self.get_logger().info("freq: %.1f" % self.freq)
        self.get_logger().info("use_nav_goal_to_start: %i" % self.use_navgoal_to_start)
        self.get_logger().info("Metrics:")
        for m in self.metrics_to_compute.keys():
            self.get_logger().info("m: %s, value: %s" % (m, self.metrics_to_compute[m]))

        if self.freq > 0.0:
            self.agents = Agents()
            self.robot = Agent()
            self.record_timer = self.create_timer(1 / self.freq, self.timer_record_callback)

        self.recording = not self.use_navgoal_to_start
        self.time_period = 3.0  # seconds
        self.last_time = self.get_clock().now()
        self.init = False

        self.agent_sub = self.create_subscription(Agents, 'human_states', self.human_callback, 1)
        self.robot_sub = self.create_subscription(Agent, 'robot_states', self.robot_callback, 1)

        # Subscribe to the robot goal to add it to the robot state
        self.goal_sub = self.create_subscription(PoseStamped, 'current_goal_pose', self.goal_callback, 1)

        self.rosout_sub = self.create_subscription(Log, '/rosout', self.rosout_callback, 10)

        self.state_timer = self.create_timer(1.0, self.check_stop_conditions)

        self._stop_lock = threading.Lock()

    def timer_record_callback(self):
        if self.init and self.recording and self.agents is not None and self.robot is not None:
            self.agents_list.append(self.agents)
            self.robot_list.append(self.robot)

    def human_callback(self, msg):
        self.init = True
        self.last_time = self.get_clock().now()
        if self.recording:
            if self.freq == 0.0:
                self.agents_list.append(msg)
            else:
                self.agents = msg

    def robot_callback(self, msg):
        self.init = True
        self.last_time = self.get_clock().now()
        if self.recording:
            robot_msg = msg
            if self.robot_goal is not None:
                robot_msg.goals.clear()
                robot_msg.goals.append(self.robot_goal.pose)
                robot_msg.goal_radius = 0.25
            if self.freq == 0.0:
                self.robot_list.append(robot_msg)
            else:
                self.robot = robot_msg

    def goal_callback(self, msg):
        self.robot_goal = msg
        if self.use_navgoal_to_start:
            self.get_logger().info("Goal received! Hunav evaluator started recording!")
            self.use_navgoal_to_start = False
            self.recording = True

    def stop_and_save(self, reason=''):
        with self._stop_lock:
            if self.recording:
                if reason:
                    self.get_logger().info(f"Hunav evaluator stopping recording due to: {reason}")
                else:
                    self.get_logger().info("Hunav evaluator stopping recording!")
                self.recording = False
                self.compute_metrics()
                rclpy.shutdown()

    def rosout_callback(self, msg: Log):
        log_msg = msg.msg.lower()
        if "goal succeeded" in log_msg or "reached the goal" in log_msg:
            self.stop_and_save(reason='Goal reached (log detected)')

    def check_stop_conditions(self):
        if self.init and self.recording:
            secs = (self.get_clock().now() - self.last_time).to_msg().sec
            if secs >= self.time_period:
                self.stop_and_save(reason='Data timeout')

    def compute_metrics(self):
        if not self.check_data():
            self.get_logger().info("Data not collected. Not computing metrics.")
            return

        agents_size = len(self.agents_list)
        robot_size = len(self.robot_list)
        self.get_logger().info(
            "Hunav evaluator. Collected %i messages of agents and %i of robot" % (agents_size, robot_size))
        self.get_logger().info("Computing metrics...")

        # compute metrics for all agents
        self.metrics_lists['time_stamps'] = hunav_metrics.get_time_stamps(self.agents_list, self.robot_list)
        for m in self.metrics_to_compute.keys():
            try:
                metric = hunav_metrics.metrics[m](self.agents_list, self.robot_list)
                self.metrics_to_compute[m] = metric[0]
                if len(metric) > 1:
                    self.metrics_lists[m] = metric[1]
            except Exception as e:
                self.metrics_to_compute[m] = None
                self.metrics_lists[m] = []

        self.get_logger().info('Metrics computed:')
        self.get_logger().info(f'{self.metrics_to_compute}')
        self.store_metrics(f"{self.output_folder}/{self.result_file_path}")

        # Now, filter according to the different behaviors
        for i in range(1, (self.number_of_behaviors + 1)):
            self.compute_metrics_behavior(i)

    def compute_metrics_behavior(self, behavior):
        beh_agents = []
        beh_robot = []
        beh_active = [0] * len(self.agents_list)
        for i, (la, lr) in enumerate(zip(self.agents_list, self.robot_list)):
            ag = Agents()
            ag.header = la.header
            for a in la.agents:
                if a.behavior.type == behavior:
                    ag.agents.append(a)
                if a.behavior.state != a.behavior.BEH_NO_ACTIVE:
                    beh_active[i] = 1
            if len(ag.agents) > 0:
                beh_agents.append(ag)
                beh_robot.append(lr)
            else:
                self.get_logger().info(f"No agents of behavior {behavior}")
                return None

        self.metrics_lists['behavior_active'] = beh_active
        for m in self.metrics_to_compute.keys():
            try:
                metric = hunav_metrics.metrics[m](beh_agents, beh_robot)
                self.metrics_to_compute[m] = metric[0]
                if len(metric) > 1:
                    self.metrics_lists[m] = metric[1]
            except Exception as e:
                self.metrics_to_compute[m] = None
                self.metrics_lists[m] = []

        self.get_logger().info(f'Metrics computed behavior {behavior}:')
        self.get_logger().info(f'{self.metrics_to_compute}')

        store_file = self.result_file_path
        if store_file.endswith(".txt"):
            store_file = store_file[:-4]
        store_file += f'_beh_{behavior}.csv'
        self.store_metrics(f"{self.output_folder}/{store_file}")

    def store_metrics(self, result_file):
        base_filename = os.path.splitext(result_file)[0]  # Remove .txt if exists
        metrics_file = base_filename + '.csv'
        steps_file = base_filename + f'_steps_{self.episode}_{self.number}.csv'

        file_exists = os.path.exists(metrics_file)

        with open(metrics_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(['experiment_tag'] + list(self.metrics_to_compute.keys()))
            row = [f"{self.episode}_{self.number}"] + [
                str(v) if v is not None else 'None' for v in self.metrics_to_compute.values()
            ]
            writer.writerow(row)

        with open(steps_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            headers = list(self.metrics_lists.keys())
            writer.writerow(headers)
            num_rows = len(self.metrics_lists['time_stamps'])
            for i in range(num_rows):
                row = []
                for m in headers:
                    metric_list = self.metrics_lists.get(m, [])
                    if len(metric_list) != 0:
                        val = metric_list[i]
                        row.append(str(val) if val is not None else 'None')
                    else:
                        row.append('None')
                writer.writerow(row)

    def check_data(self):
        agents_size = len(self.agents_list)
        robot_size = len(self.robot_list)
        if agents_size == 0 and robot_size == 0:
            return False
        if abs(agents_size - robot_size) != 0:
            while len(self.agents_list) > len(self.robot_list):
                self.agents_list.pop()
            while len(self.robot_list) > len(self.agents_list):
                self.robot_list.pop()
        # check that the robot msg contains a goal?
        # check when the robot reaches the goal?
        return True


def main(args=None):
    rclpy.init(args=args)
    node = HunavEvaluatorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()