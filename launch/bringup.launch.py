from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    namespace_arg = DeclareLaunchArgument('namespace', default_value='rob1')
    robot_ip_arg = DeclareLaunchArgument('robot_ip', default_value='192.168.1.10')
    robot_streaming_port_arg = DeclareLaunchArgument('robot_streaming_port', default_value='30101')
    robot_state_port_arg = DeclareLaunchArgument('robot_state_port', default_value='30201')
    sequence_check_mode_arg = DeclareLaunchArgument('sequence_check_mode', default_value='none')

    node = Node(
        package='compas_rrc_driver',
        executable='driver',
        namespace=LaunchConfiguration('namespace'),
        output='screen',
        parameters=[
            {
                'robot_ip_address': LaunchConfiguration('robot_ip'),
                'robot_streaming_port': LaunchConfiguration('robot_streaming_port'),
                'robot_state_port': LaunchConfiguration('robot_state_port'),
                'sequence_check_mode': LaunchConfiguration('sequence_check_mode'),
            }
        ],
    )

    return LaunchDescription([
        namespace_arg,
        robot_ip_arg,
        robot_streaming_port_arg,
        robot_state_port_arg,
        sequence_check_mode_arg,
        node,
    ])
