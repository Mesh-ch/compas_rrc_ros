#!/bin/bash
set -e

# Source ROS distro environment and local ROS 2 workspace
source "/opt/ros/$ROS_DISTRO/setup.bash"
if [ -f "/root/ros2_ws/install/setup.bash" ]; then
  source "/root/ros2_ws/install/setup.bash"
fi

exec "$@"
