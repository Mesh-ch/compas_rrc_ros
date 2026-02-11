# Container for running COMPAS RRC Driver on ROS 2
#
# Build:
#   docker build --rm -f Dockerfile -t compasrrc/compas_rrc_driver:ros2 .
#
# Usage:
#   docker run --rm -it --net=host compasrrc/compas_rrc_driver:ros2

FROM ros:humble-ros-core
LABEL maintainer="RRC Team <rrc@arch.ethz.ch>"

SHELL ["/bin/bash", "-c"]

# Build number
ENV RRC_BUILD=2
ENV ROS_WS=/root/ros2_ws

RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    python3-colcon-common-extensions \
    python3-rosdep \
    && rm -rf /var/lib/apt/lists/*

# Add COMPAS RRC Driver package
RUN mkdir -p ${ROS_WS}/src
ADD . ${ROS_WS}/src/compas_rrc_driver
WORKDIR ${ROS_WS}

RUN source /opt/ros/${ROS_DISTRO}/setup.bash \
    && if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi \
    && rosdep update \
    && rosdep install -y --from-paths src --ignore-src --rosdistro ${ROS_DISTRO} \
    && colcon build --packages-select compas_rrc_driver \
    && rm -rf /var/lib/apt/lists/*

COPY ./.docker/ros2_colcon_entrypoint.sh /ros2_colcon_entrypoint.sh
RUN chmod +x /ros2_colcon_entrypoint.sh

ENTRYPOINT ["/ros2_colcon_entrypoint.sh"]
CMD ["bash"]
