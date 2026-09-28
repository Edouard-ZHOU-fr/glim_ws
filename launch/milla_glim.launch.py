import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    milla_glim_processor = Node(
        package='glim_ros',
        executable='glim_rosnode',
        name='milla_glim_processor',
        output='screen',
        sigterm_timeout='30.0' )


    localization_conventor = Node(
        package='convert_gnss',
        executable='converter',
        name='localization_conventor',
        output='log',
        parameters=[os.path.join(get_package_share_directory('convert_gnss'), 'config', 'config.yaml')]
    )

    return LaunchDescription([
        milla_glim_processor,
        localization_conventor
    ])
