from dataclasses import dataclass
import os
from os import environ, pathsep
from scripts import GazeboRosPaths
from ament_index_python.packages import get_package_prefix
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, SetLaunchConfiguration, SetEnvironmentVariable,
                            RegisterEventHandler, LogInfo, TimerAction)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessStart
from launch.substitutions import PathJoinSubstitution, LaunchConfiguration, EnvironmentVariable, PythonExpression
from launch_pal.actions import CheckPublicSim
from launch_pal.arg_utils import LaunchArgumentsBase
from launch_pal.include_utils import include_scoped_launch_py_description
from launch_pal.robot_arguments import CommonArgs
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from omni_base_description.launch_arguments import OmniBaseArgs


@dataclass(frozen=True)
class LaunchArguments(LaunchArgumentsBase):
    wheel_model: DeclareLaunchArgument = OmniBaseArgs.wheel_model
    laser_model: DeclareLaunchArgument = OmniBaseArgs.laser_model
    add_on_module: DeclareLaunchArgument = OmniBaseArgs.add_on_module
    camera_model: DeclareLaunchArgument = OmniBaseArgs.camera_model
    is_public_sim: DeclareLaunchArgument = CommonArgs.is_public_sim
    world_name: DeclareLaunchArgument = CommonArgs.world_name
    navigation: DeclareLaunchArgument = CommonArgs.navigation
    slam: DeclareLaunchArgument = CommonArgs.slam
    advanced_navigation: DeclareLaunchArgument = CommonArgs.advanced_navigation
    docking: DeclareLaunchArgument = CommonArgs.docking
    x: DeclareLaunchArgument = CommonArgs.x
    y: DeclareLaunchArgument = CommonArgs.y
    yaw: DeclareLaunchArgument = CommonArgs.yaw


def generate_launch_description():

    # Create the launch description and populate
    ld = LaunchDescription()
    launch_arguments = LaunchArguments()

    launch_arguments.add_to_launch_description(ld)

    declare_actions(ld, launch_arguments)

    return ld


def declare_actions(
    launch_description: LaunchDescription, launch_args: LaunchArguments
):
    # Set use_sim_time to True
    set_sim_time = SetLaunchConfiguration('use_sim_time', 'True')
    launch_description.add_action(set_sim_time)

    # Shows error if is_public_sim is not set to True when using public simulation
    public_sim_check = CheckPublicSim()
    launch_description.add_action(public_sim_check)

    robot_name = 'omni_base'

    # Set environment variables
    packages = ['omni_base_description', 'pal_gazebo_worlds']
    model_path = get_model_paths(packages)

    hunav_models = PathJoinSubstitution([
        FindPackageShare('test_hunav'),
        'models',
    ])

    gazebo_model_path_env_var = SetEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=[model_path, hunav_models]
    )

    _, plugin, _ = GazeboRosPaths.get_paths()

    if 'GAZEBO_PLUGIN_PATH' in environ:
        plugin += pathsep + environ['GAZEBO_PLUGIN_PATH']

    set_env_gazebo_resource = SetEnvironmentVariable(
        name='GAZEBO_RESOURCE_PATH',
        value=[EnvironmentVariable('GAZEBO_RESOURCE_PATH'), model_path, hunav_models]
    )
    set_env_gazebo_plugin = SetEnvironmentVariable(
        name='GAZEBO_PLUGIN_PATH',
        value=[EnvironmentVariable('GAZEBO_PLUGIN_PATH'), plugin]
    )

    launch_description.add_action(gazebo_model_path_env_var)
    launch_description.add_action(set_env_gazebo_resource)
    launch_description.add_action(set_env_gazebo_plugin)

    # Declare hunav launch arguments
    declare_agents_conf_file = DeclareLaunchArgument(
        'configuration_file', default_value='test.yaml',
        description='Specify configuration file name in the cofig directory'
    )
    declare_metrics_conf_file = DeclareLaunchArgument(
        'metrics_file', default_value='metrics.yaml',
        description='Specify the name of the metrics configuration file in the cofig directory'
    )
    declare_arg_world = DeclareLaunchArgument(
        'base_world', default_value='no_roof_small_warehouse.world',
        description='Specify world file name'
    )
    declare_gz_obs = DeclareLaunchArgument(
        'use_gazebo_obs', default_value='True',
        description='Whether to fill the agents obstacles with closest Gazebo obstacle or not'
    )
    declare_update_rate = DeclareLaunchArgument(
        'update_rate', default_value='10.0',
        description='Update rate of the plugin'
    )
    # declare_robot_name = DeclareLaunchArgument(
    #     'robot_name', default_value='pmb2',
    #     description='Specify the name of the robot Gazebo model'
    # )
    declare_frame_to_publish = DeclareLaunchArgument(
        'global_frame_to_publish', default_value='map',
        description='Name of the global frame in which the position of the agents are provided'
    )
    declare_use_navgoal = DeclareLaunchArgument(
        'use_navgoal_to_start', default_value='True',
        description='Whether to start the agents movements when a navigation goal is received or not'
    )
    declare_navgoal_topic = DeclareLaunchArgument(
        'navgoal_topic', default_value='current_goal_pose',  # goal_pose  amcl_pose  initialpose  current_goal_pose
        description='Name of the topic in which navigation goal for the robot will be published'
    )
    declare_navigation = DeclareLaunchArgument(
        'navigation', default_value='False',
        description='If launch the robot navigation system'
    )
    declare_ignore_models = DeclareLaunchArgument(
        'ignore_models', default_value='ground_plane',  # ground_plane
        description='list of Gazebo models that the agents should ignore as obstacles as the ground_plane. Indicate the models with a blank space between them'
    )  # !！!
    declare_arg_verbose = DeclareLaunchArgument(
        'verbose', default_value='False',
        description='Set "True" to increase messages written to terminal.'
    )

    launch_description.add_action(declare_agents_conf_file)
    launch_description.add_action(declare_metrics_conf_file)
    launch_description.add_action(declare_arg_world)
    launch_description.add_action(declare_gz_obs)
    launch_description.add_action(declare_update_rate)
    # launch_description.add_action(declare_robot_name)
    launch_description.add_action(declare_frame_to_publish)
    launch_description.add_action(declare_use_navgoal)
    launch_description.add_action(declare_navgoal_topic)
    launch_description.add_action(declare_navigation)
    launch_description.add_action(declare_ignore_models)
    launch_description.add_action(declare_arg_verbose)

    # World generation parameters
    world_file_name = LaunchConfiguration('base_world')
    gz_obs = LaunchConfiguration('use_gazebo_obs')
    rate = LaunchConfiguration('update_rate')
    # robot_name = LaunchConfiguration('robot_name')
    global_frame = LaunchConfiguration('global_frame_to_publish')
    use_navgoal = LaunchConfiguration('use_navgoal_to_start')
    navgoal_topic = LaunchConfiguration('navgoal_topic')
    # navigation = LaunchConfiguration('navigation')
    ignore_models = LaunchConfiguration('ignore_models')

    # Hunav agent configuration file
    agent_conf_file = PathJoinSubstitution([
        FindPackageShare('hunav_agent_manager'),
        'config',
        LaunchConfiguration('configuration_file')
    ])

    # Read the yaml file and load the parameters
    hunav_loader_node = Node(
        package='hunav_agent_manager',
        executable='hunav_loader',
        output='screen',
        parameters=[agent_conf_file]
    )

    launch_description.add_action(hunav_loader_node)

    # World base file
    world_file = PathJoinSubstitution([
        FindPackageShare('pal_gazebo_worlds'),
        'worlds',
        world_file_name
    ])

    # the node looks for the base_world file in the directory 'worlds'
    # of the package hunav_gazebo_plugin directly. So we do not need to
    # indicate the path
    hunav_gazebo_worldgen_node = Node(
        package='test_hunav',
        executable='hunav_gazebo_world_generator',
        output='screen',
        parameters=[{'base_world': world_file},
                    {'use_gazebo_obs': gz_obs},
                    {'update_rate': rate},
                    {'robot_name': robot_name},
                    {'global_frame_to_publish': global_frame},
                    {'use_navgoal_to_start': use_navgoal},
                    {'navgoal_topic': navgoal_topic},
                    {'ignore_models': ignore_models}]
        # arguments=['--ros-args', '--params-file', conf_file]
    )

    ordered_launch_event = RegisterEventHandler(
        OnProcessStart(
            target_action=hunav_loader_node,
            on_start=[
                LogInfo(msg='HunNavLoader started, launching HuNav_Gazebo_world_generator after 3 seconds...'),
                TimerAction(
                    period=3.0,
                    actions=[hunav_gazebo_worldgen_node],
                )
            ]
        )
    )

    launch_description.add_action(ordered_launch_event)

    # hunav_manager node
    hunav_manager_node = Node(
        package='hunav_agent_manager',
        executable='hunav_agent_manager',
        name='hunav_agent_manager',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    launch_description.add_action(hunav_manager_node)

    # # hunav_evaluator node
    # metrics_file = PathJoinSubstitution([
    #     FindPackageShare('hunav_evaluator'),
    #     'config',
    #     LaunchConfiguration('metrics_file')
    # ])
    #
    # launch_description.add_action(DeclareLaunchArgument('number', default_value='0'))
    # launch_description.add_action(DeclareLaunchArgument('episode', default_value='0'))
    #
    # hunav_evaluator_node = Node(
    #     package='hunav_evaluator',
    #     executable='hunav_evaluator_node',
    #     output='screen',
    #     parameters=[
    #         metrics_file,
    #         {'number': LaunchConfiguration('number')},
    #         {'episode': LaunchConfiguration('episode')}
    #     ]
    # )
    #
    # launch_description.add_action(hunav_evaluator_node)

    # Launch the generated world in Gazebo
    gazebo = include_scoped_launch_py_description(
        pkg_name='pal_gazebo_worlds',
        paths=['launch', 'pal_gazebo.launch.py'],
        env_vars=[gazebo_model_path_env_var],
        launch_arguments={
            'world_name': 'generatedWorld',  # ！!！
            'model_paths': packages,
            'resource_paths': packages,
        })

    gz_launch_event = RegisterEventHandler(
        OnProcessStart(
            target_action=hunav_gazebo_worldgen_node,
            on_start=[
                LogInfo(msg='GenerateWorld started, launching Gazebo after 3 seconds...'),
                TimerAction(
                    period=3.0,
                    actions=[gazebo],
                )
            ]
        )
    )

    launch_description.add_action(gz_launch_event)

    # DO NOT Launch this if any robot localization is launched
    static_tf_node = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        output='screen',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom'],
        # other option: arguments = "0 0 0 0 0 0 pmb2 base_footprint".split(' ')
        condition=UnlessCondition(LaunchConfiguration('navigation'))
    )
    launch_description.add_action(static_tf_node)

    navigation = include_scoped_launch_py_description(
        pkg_name='omni_base_2dnav',
        paths=['launch', 'omni_base_nav_bringup.launch.py'],
        launch_arguments={
            'robot_name': robot_name,
            'laser': launch_args.laser_model,
            'is_public_sim': launch_args.is_public_sim,
            'advanced_navigation': launch_args.advanced_navigation,
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'world_name': 'generatedWorld',  # ！!！
            'slam': launch_args.slam,
        },
        condition=IfCondition(LaunchConfiguration('navigation')))

    launch_description.add_action(navigation)

    advanced_navigation = include_scoped_launch_py_description(
        pkg_name='omni_base_advanced_2dnav',
        paths=['launch', 'omni_base_advanced_nav_bringup.launch.py'],
        condition=IfCondition(LaunchConfiguration('advanced_navigation')))

    launch_description.add_action(advanced_navigation)

    docking = include_scoped_launch_py_description(
        pkg_name='omni_base_docking',
        paths=['launch', 'omni_base_docking_bringup.launch.py'],
        condition=IfCondition(
            PythonExpression(
                [
                    "'",
                    LaunchConfiguration('docking'),
                    "' == 'True' or '",
                    LaunchConfiguration('advanced_navigation'),
                    "' == 'True'"
                ]
            )
        )
    )

    launch_description.add_action(docking)

    robot_spawn = include_scoped_launch_py_description(
        pkg_name='omni_base_gazebo',
        paths=['launch', 'robot_spawn.launch.py'],
        launch_arguments={
            'robot_name': robot_name,
            'x': launch_args.x,
            'y': launch_args.y,
            'yaw': launch_args.yaw,
        }
    )

    launch_description.add_action(robot_spawn)

    omni_base_bringup = include_scoped_launch_py_description(
        pkg_name='omni_base_bringup', paths=['launch', 'omni_base_bringup.launch.py'],
        launch_arguments={
            'wheel_model': launch_args.wheel_model,
            'laser_model': launch_args.laser_model,
            'add_on_module': launch_args.add_on_module,
            'camera_model': launch_args.camera_model,
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'is_public_sim': launch_args.is_public_sim,
        }
    )

    launch_description.add_action(omni_base_bringup)

    launch_description.add_action(DeclareLaunchArgument('x', default_value='0.0'))
    launch_description.add_action(DeclareLaunchArgument('y', default_value='0.0'))
    launch_description.add_action(DeclareLaunchArgument('yaw', default_value='0.0'))

    publish_initial_pose_node = Node(
        package='ethical_testing',
        executable='publish_initial_pose',
        output='screen',
        parameters=[
            {'x': LaunchConfiguration('x')},
            {'y': LaunchConfiguration('y')},
            {'yaw': LaunchConfiguration('yaw')}
        ]
    )

    launch_description.add_action(publish_initial_pose_node)


def get_model_paths(packages_names):
    model_paths = ''
    for package_name in packages_names:
        if model_paths != '':
            model_paths += pathsep

        package_path = get_package_prefix(package_name)
        model_path = os.path.join(package_path, 'share')

        model_paths += model_path

    if 'GAZEBO_MODEL_PATH' in environ:
        model_paths += pathsep + environ['GAZEBO_MODEL_PATH']

    return model_paths
