import os
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
        output='log'
    )

    return LaunchDescription([
        milla_glim_processor,
        localization_conventor
    ])
