# Container for running COMPAS RRC Driver on ROS 2
#
# Build:
#   docker build --rm -f Dockerfile -t compasrrc/compas_rrc_driver:ros2 .
#
# Usage:
#   docker run --rm -it --net=host compasrrc/compas_rrc_driver:ros2

FROM ros:jazzy-ros-base AS builder
LABEL maintainer="Martin Inauen <inauen@mesh.ch>""

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-colcon-common-extensions \
    ros-jazzy-rosbridge-suite \
    ros-jazzy-rosidl-default-generators \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root/ros2_ws
COPY . /root/ros2_ws

# Ensure host-generated ROS/colcon artifacts are not used in container builds.
RUN rm -rf /root/ros2_ws/build /root/ros2_ws/install /root/ros2_ws/log \
    && source /opt/ros/${ROS_DISTRO}/setup.bash \
    && colcon build --base-paths . --packages-select compas_rrc_driver --merge-install

FROM ros:jazzy-ros-base AS runtime

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-rosbridge-suite \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root/ros2_ws
COPY --from=builder /root/ros2_ws/install /root/ros2_ws/install
COPY .docker/ros2_colcon_entrypoint.sh /ros2_colcon_entrypoint.sh

RUN chmod +x /ros2_colcon_entrypoint.sh

ENTRYPOINT ["/ros2_colcon_entrypoint.sh"]
CMD ["bash"]
