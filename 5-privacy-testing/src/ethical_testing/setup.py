from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'ethical_testing'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('ethical_testing/config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='gssi-lab',
    maintainer_email='gssi-lab@todo.todo',
    description='ethical_testing',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'spawn_model = ethical_testing.spawn_model:main',
            'cmd_behaviors = ethical_testing.cmd_behaviors:main',
            'navigate_to_pose_action = ethical_testing.navigate_to_pose_action:main',
            'navigate_to_pose_collision_detection = ethical_testing.navigate_to_pose_collision_detection:main',
            'waypoint_follower = ethical_testing.waypoint_follower:main',
            'waypoint_check = ethical_testing.waypoint_check:main',
            'hunav_loader = ethical_testing.hunav_loader:main',
            'laser_scan_subscriber = ethical_testing.laser_scan_subscriber:main',
            'pointcloud_subscriber = ethical_testing.pointcloud_subscriber:main',
            'publish_initial_pose = ethical_testing.publish_initial_pose:main',
            'ethical_hunav = ethical_testing.ethical_hunav:main',
            'generate_restricted_yaml = ethical_testing.generate_restricted_yaml:main',
            'ethical_navigation = ethical_testing.ethical_navigation:main',
            'waypoints = ethical_testing.config.waypoints:main',
            'ga_privacy = ethical_testing.ga_privacy:main',
            'rs_privacy = ethical_testing.rs_privacy:main',

        ],
    },
)
