import subprocess
import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import SpawnEntity, DeleteEntity


areas = [
    "Boxes 1", "Boxes 2", "Boxes 3",
    "Shelf 1", "Shelf 2", "Shelf 3", "Shelf 4", "Shelf 5", "Shelf 6",
    "Waste Area", "Area 1", "Area 2", "Area 3", "Area 4", "Area 5", "Pallet Jack",
    "Large Shelf 1", "Large Shelf 2", "Large Shelf 3", "Large Shelf 4"
]


area_map_waypoints = {
    "Boxes 1": ["A1", "B1", "C1", "D1", "E1", "E2", "E3"],
    "Boxes 2": ["E3", "E4", "E5", "E6"],
    "Boxes 3": ["E6", "E7", "E8", "D9", "C9", "B9", "A9"],
    "Shelf 1": ["A9", "B9", "C9", "D9", "A12", "B12", "C12", "D12"],
    "Shelf 2": ["A12", "B12", "C12", "D12", "A14", "B14", "C14", "D14"],
    "Shelf 3": ["A14", "B14", "C14", "D14", "A16", "B16", "C16", "D16"],
    "Shelf 4": ["A16", "B16", "C16", "D16", "A18", "B18", "C18", "D18"],
    "Shelf 5": ["A18", "B18", "C18", "D18", "A20", "B20", "C20", "D20"],
    "Shelf 6": ["A20", "B20", "C20", "D20", "A22", "B22", "C22", "D22"],
    "Waste Area": ["F3", "G3"],
    "Area 1": ["G4", "G5", "G6", "G7", "H4", "I4", "J4"],
    "Area 2": ["G7", "G8", "G9", "G10"],
    "Area 3": ["G11", "G12", "G13", "G14", "H11", "H12", "H13", "H14", "I11", "I12", "I13", "I14", "J11", "J12", "J13", "J14"],
    "Area 4": ["G15", "G16", "G17", "H15", "H16", "H17", "I15", "I16", "I17", "J15", "J16", "J17"],
    "Area 5": ["G18", "G19", "G20", "G21", "H18", "H19", "H20", "H21"],
    "Pallet Jack": ["F22", "G21", "H21", "I22"],
    "Large Shelf 1": ["M2", "M3", "M4", "M5", "M6", "M7"],
    "Large Shelf 2": ["M8", "M9", "M10", "M11", "M12"],
    "Large Shelf 3": ["M13", "M14", "M15", "M16", "M17"],
    "Large Shelf 4": ["M18", "M19", "M20", "M21", "M22"]
}


waypoints = {
    "A1": {"x": 5.8, "y": 9.8},
    "B1": {"x": 4.8, "y": 9.8},
    "C1": {"x": 3.8, "y": 9.8},
    "D1": {"x": 2.8, "y": 9.8},
    "E1": {"x": 1.75, "y": 9.8},
    "K1": {"x": -2.95, "y": 9.8},
    "L1": {"x": -3.8, "y": 9.8},
    "M1": {"x": -4.4, "y": 9.8},

    "E2": {"x": 1.75, "y": 8.8},
    "K2": {"x": -2.95, "y": 8.8},
    "L2": {"x": -3.8, "y": 8.8},
    "M2": {"x": -4.4, "y": 8.8},

    "E3": {"x": 1.75, "y": 7.8},
    "F3": {"x": 0.8, "y": 7.8},
    "G3": {"x": -0.1, "y": 7.8},
    "K3": {"x": -2.95, "y": 7.8},
    "L3": {"x": -3.8, "y": 7.8},
    "M3": {"x": -4.4, "y": 7.8},

    "E4": {"x": 1.75, "y": 6.8},
    "F4": {"x": 0.8, "y": 6.8},
    "G4": {"x": -0.1, "y": 6.8},
    "H4": {"x": -0.9, "y": 6.8},
    "I4": {"x": -1.6, "y": 6.8},
    "J4": {"x": -2.3, "y": 6.8},
    "K4": {"x": -2.95, "y": 6.8},
    "L4": {"x": -3.8, "y": 6.8},
    "M4": {"x": -4.4, "y": 6.8},

    "E5": {"x": 1.75, "y": 5.85},
    "F5": {"x": 0.8, "y": 5.85},
    "G5": {"x": -0.1, "y": 5.85},
    "K5": {"x": -2.95, "y": 5.85},
    "L5": {"x": -3.8, "y": 5.85},
    "M5": {"x": -4.4, "y": 5.85},

    "E6": {"x": 1.75, "y": 4.9},
    "F6": {"x": 0.8, "y": 4.9},
    "G6": {"x": -0.1, "y": 4.9},
    "K6": {"x": -2.95, "y": 4.9},
    "L6": {"x": -3.8, "y": 4.9},
    "M6": {"x": -4.4, "y": 4.9},

    "E7": {"x": 1.75, "y": 3.95},
    "F7": {"x": 0.8, "y": 3.95},
    "G7": {"x": -0.1, "y": 3.95},
    "K7": {"x": -2.95, "y": 3.95},
    "L7": {"x": -3.8, "y": 3.95},
    "M7": {"x": -4.4, "y": 3.95},

    "E8": {"x": 1.75, "y": 3.0},
    "F8": {"x": 0.8, "y": 3.0},
    "G8": {"x": -0.1, "y": 3.0},
    "K8": {"x": -2.95, "y": 3.0},
    "L8": {"x": -3.8, "y": 3.0},
    "M8": {"x": -4.4, "y": 3.0},

    "A9": {"x": 5.8, "y": 2.1},
    "B9": {"x": 4.8, "y": 2.1},
    "C9": {"x": 3.8, "y": 2.1},
    "D9": {"x": 2.8, "y": 2.1},
    "E9": {"x": 1.75, "y": 2.1},
    "F9": {"x": 0.8, "y": 2.1},
    "G9": {"x": -0.1, "y": 2.1},
    "K9": {"x": -2.95, "y": 2.1},
    "L9": {"x": -3.8, "y": 2.1},
    "M9": {"x": -4.4, "y": 2.1},

    "E10": {"x": 1.75, "y": 1.3},
    "F10": {"x": 0.8, "y": 1.3},
    "G10": {"x": -0.1, "y": 1.3},
    "K10": {"x": -2.95, "y": 1.3},
    "L10": {"x": -3.8, "y": 1.3},
    "M10": {"x": -4.4, "y": 1.3},

    "E11": {"x": 1.75, "y": 0.5},
    "F11": {"x": 0.8, "y": 0.5},
    "G11": {"x": -0.1, "y": 0.5},
    "H11": {"x": -0.9, "y": 0.5},
    "I11": {"x": -1.6, "y": 0.5},
    "J11": {"x": -2.3, "y": 0.5},
    "K11": {"x": -2.95, "y": 0.5},
    "L11": {"x": -3.8, "y": 0.5},
    "M11": {"x": -4.4, "y": 0.5},

    "A12": {"x": 5.8, "y": -0.35},
    "B12": {"x": 4.8, "y": -0.35},
    "C12": {"x": 3.8, "y": -0.35},
    "D12": {"x": 2.8, "y": -0.35},
    "E12": {"x": 1.75, "y": -0.35},
    "F12": {"x": 0.8, "y": -0.35},
    "G12": {"x": -0.1, "y": -0.35},
    "H12": {"x": -0.9, "y": -0.35},
    "I12": {"x": -1.6, "y": -0.35},
    "J12": {"x": -2.3, "y": -0.35},
    "K12": {"x": -2.95, "y": -0.35},
    "L12": {"x": -3.8, "y": -0.35},
    "M12": {"x": -4.4, "y": -0.35},

    "E13": {"x": 1.75, "y": -1.25},
    "F13": {"x": 0.8, "y": -1.25},
    "G13": {"x": -0.1, "y": -1.25},
    "H13": {"x": -0.9, "y": -1.25},
    "I13": {"x": -1.6, "y": -1.25},
    "J13": {"x": -2.3, "y": -1.25},
    "K13": {"x": -2.95, "y": -1.25},
    "L13": {"x": -3.8, "y": -1.25},
    "M13": {"x": -4.4, "y": -1.25},

    "A14": {"x": 5.8, "y": -2.15},
    "B14": {"x": 4.8, "y": -2.15},
    "C14": {"x": 3.8, "y": -2.15},
    "D14": {"x": 2.8, "y": -2.15},
    "E14": {"x": 1.75, "y": -2.15},
    "F14": {"x": 0.8, "y": -2.15},
    "G14": {"x": -0.1, "y": -2.15},
    "H14": {"x": -0.9, "y": -2.15},
    "I14": {"x": -1.6, "y": -2.15},
    "J14": {"x": -2.3, "y": -2.15},
    "K14": {"x": -2.95, "y": -2.15},
    "L14": {"x": -3.8, "y": -2.15},
    "M14": {"x": -4.4, "y": -2.15},

    "E15": {"x": 1.75, "y": -3.05},
    "F15": {"x": 0.8, "y": -3.05},
    "G15": {"x": -0.1, "y": -3.05},
    "H15": {"x": -0.9, "y": -3.05},
    "I15": {"x": -1.6, "y": -3.05},
    "J15": {"x": -2.3, "y": -3.05},
    "K15": {"x": -2.95, "y": -3.05},
    "L15": {"x": -3.8, "y": -3.05},
    "M15": {"x": -4.4, "y": -3.05},

    "A16": {"x": 5.8, "y": -3.95},
    "B16": {"x": 4.8, "y": -3.95},
    "C16": {"x": 3.8, "y": -3.95},
    "D16": {"x": 2.8, "y": -3.95},
    "E16": {"x": 1.75, "y": -3.95},
    "F16": {"x": 0.8, "y": -3.95},
    "G16": {"x": -0.1, "y": -3.95},
    "H16": {"x": -0.9, "y": -3.95},
    "I16": {"x": -1.6, "y": -3.95},
    "J16": {"x": -2.3, "y": -3.95},
    "K16": {"x": -2.95, "y": -3.95},
    "L16": {"x": -3.8, "y": -3.95},
    "M16": {"x": -4.4, "y": -3.95},

    "E17": {"x": 1.75, "y": -4.85},
    "F17": {"x": 0.8, "y": -4.85},
    "G17": {"x": -0.1, "y": -4.85},
    "H17": {"x": -0.9, "y": -4.85},
    "I17": {"x": -1.6, "y": -4.85},
    "J17": {"x": -2.3, "y": -4.85},
    "K17": {"x": -2.95, "y": -4.85},
    "L17": {"x": -3.8, "y": -4.85},
    "M17": {"x": -4.4, "y": -4.85},

    "A18": {"x": 5.8, "y": -5.8},
    "B18": {"x": 4.8, "y": -5.8},
    "C18": {"x": 3.8, "y": -5.8},
    "D18": {"x": 2.8, "y": -5.8},
    "E18": {"x": 1.75, "y": -5.8},
    "F18": {"x": 0.8, "y": -5.8},
    "G18": {"x": -0.1, "y": -5.8},
    "H18": {"x": -0.9, "y": -5.8},
    "K18": {"x": -2.95, "y": -5.8},
    "L18": {"x": -3.8, "y": -5.8},
    "M18": {"x": -4.4, "y": -5.8},

    "E19": {"x": 1.75, "y": -6.75},
    "F19": {"x": 0.8, "y": -6.75},
    "G19": {"x": -0.1, "y": -6.75},
    "H19": {"x": -0.9, "y": -6.75},
    "K19": {"x": -2.95, "y": -6.75},
    "L19": {"x": -3.8, "y": -6.75},
    "M19": {"x": -4.4, "y": -6.75},

    "A20": {"x": 5.8, "y": -7.75},
    "B20": {"x": 4.8, "y": -7.75},
    "C20": {"x": 3.8, "y": -7.75},
    "D20": {"x": 2.8, "y": -7.75},
    "E20": {"x": 1.75, "y": -7.75},
    "F20": {"x": 0.8, "y": -7.75},
    "G20": {"x": -0.1, "y": -7.75},
    "H20": {"x": -0.9, "y": -7.75},
    "K20": {"x": -2.95, "y": -7.75},
    "L20": {"x": -3.8, "y": -7.75},
    "M20": {"x": -4.4, "y": -7.75},

    "E21": {"x": 1.75, "y": -8.6},
    "F21": {"x": 0.8, "y": -8.6},
    "G21": {"x": -0.1, "y": -8.6},
    "H21": {"x": -0.9, "y": -8.6},
    "K21": {"x": -2.95, "y": -8.6},
    "L21": {"x": -3.8, "y": -8.6},
    "M21": {"x": -4.4, "y": -8.6},

    "A22": {"x": 5.8, "y": -9.7},
    "B22": {"x": 4.8, "y": -9.7},
    "C22": {"x": 3.8, "y": -9.7},
    "D22": {"x": 2.8, "y": -9.7},
    "E22": {"x": 1.75, "y": -9.45},
    "F22": {"x": 0.8, "y": -9.45},
    "I22": {"x": -1.6, "y": -9.45},
    "J22": {"x": -2.3, "y": -9.45},
    "K22": {"x": -2.95, "y": -9.45},
    "L22": {"x": -3.8, "y": -9.45},
    "M22": {"x": -4.4, "y": -9.45},
}


def check_waypoints():
    # ros2 service call /set_entity_state gazebo_msgs/srv/SetEntityState "{state: {name: 'citizen_extras_female_02', pose: {position: {x: 1.0, y: 2.0, z: 0}}}}"
    for key, value in waypoints.items():
        process = subprocess.Popen(
            f"""ros2 service call /set_entity_state gazebo_msgs/srv/SetEntityState "{{state: {{name: 'citizen_extras_female_02', pose: {{position: {{x: {value['x']}, y: {value['y']}, z: 0}}}}}}}}" """,
            shell=True)
        process.wait()


class WaypointBallSpawner(Node):

    def __init__(self):
        super().__init__('waypoint_ball_spawner')
        self.spawn_cli = self.create_client(SpawnEntity, '/spawn_entity')
        self.delete_cli = self.create_client(DeleteEntity, '/delete_entity')
        while not self.spawn_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for /spawn_entity service...')
        while not self.delete_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for /delete_entity service...')
        self.spawn_balls()

    def spawn_balls(self):

        ball_template = '''
        <sdf version="1.6">
          <model name="{name}">
            <static>true</static>
            <link name="ball">
              <visual name="visual">
                <geometry>
                  <sphere>
                    <radius>0.15</radius>
                  </sphere>
                </geometry>
                <material>
                  <ambient>0 0 1 1</ambient>
                  <diffuse>0 0 1 1</diffuse>
                  <specular>0.2 0.2 0.2 1</specular>
                </material>
              </visual>
              <collision name="collision">
                <geometry>
                  <sphere>
                    <radius>0.15</radius>
                  </sphere>
                </geometry>
              </collision>
            </link>
          </model>
        </sdf>
        '''

        for name, pos in waypoints.items():
            model_name = f'waypoint_{name}'

            del_req = DeleteEntity.Request()
            del_req.name = model_name
            del_future = self.delete_cli.call_async(del_req)
            rclpy.spin_until_future_complete(self, del_future)
            del_result = del_future.result()
            if del_result and del_result.success:
                self.get_logger().info(f"Deleted old {model_name}")
            else:
                self.get_logger().info(f"No existing {model_name} to delete, or already gone.")

            sdf = ball_template.format(name=model_name)
            spawn_req = SpawnEntity.Request()
            spawn_req.name = model_name
            spawn_req.xml = sdf
            spawn_req.robot_namespace = ''
            spawn_req.reference_frame = 'world'
            spawn_req.initial_pose.position.x = pos['x']
            spawn_req.initial_pose.position.y = pos['y']
            spawn_req.initial_pose.position.z = 0.15
            spawn_req.initial_pose.orientation.w = 1.0
            spawn_future = self.spawn_cli.call_async(spawn_req)
            rclpy.spin_until_future_complete(self, spawn_future)
            result = spawn_future.result()
            if result.success:
                self.get_logger().info(f'Successfully spawned {model_name}')
            else:
                self.get_logger().error(f'Failed to spawn {model_name}: {result.status_message}')


def main(args=None):

    # check_waypoints()

    rclpy.init(args=args)
    node = WaypointBallSpawner()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()