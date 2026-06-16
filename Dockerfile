# Container for running COMPAS RRC Driver on ROS 2
#
# Build:
#   docker build --rm -f Dockerfile -t compasrrc/compas_rrc_driver:ros2 .
#
# Usage:
#   docker run --rm -it --net=host compasrrc/compas_rrc_driver:ros2

FROM ghcr.io/prefix-dev/pixi:latest
LABEL maintainer="RRC Team <rrc@arch.ethz.ch>"

SHELL ["/bin/bash", "-c"]

# Build number
ENV RRC_BUILD=2

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Add repository and build in-place with Pixi
WORKDIR /workspace
ADD . /workspace

# Ensure host-generated ROS/colcon artifacts are not used in container builds.
RUN rm -rf /workspace/build /workspace/install /workspace/log

RUN COLCON_CURRENT_PREFIX=/workspace/install pixi install \
    && COLCON_CURRENT_PREFIX=/workspace/install pixi run build \
    && rm -rf /var/lib/apt/lists/*
CMD ["bash"]
