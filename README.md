# COMPAS RRC: ROS 2 driver

![COMPAS RRC](images/compas_rrc.png)

> ROS 2 package for the COMPAS RRC driver for ABB robots.

## ROS 2 Usage

### Pixi-managed environment (recommended)

This repository provides a `pixi.toml` with a ROS 2 Jazzy environment based on
`conda-forge` and `robostack-jazzy`, including `ros-jazzy-rosbridge-suite`.

Install Pixi and create the environment:

```bash
cd ~/ros2_ws/src
git clone https://github.com/compas-rrc/compas_rrc_ros.git
cd compas_rrc_ros
pixi install
```

Build and run the package via Pixi tasks:

```bash
pixi run build
```

Run compas driver:

```bash
pixi run ros2 launch compas_rrc_driver bringup.launch.py robot_ip:=127.0.0.1
```

Run rosbridge websocket server:

```bash
pixi run ros2 launch rosbridge_server rosbridge_websocket_launch.xml unregister_timeout:=28800
```

If you want an interactive session for multiple ROS 2 commands, you can still
open a Pixi shell:

```bash
pixi shell
ros2 topic list
ros2 service list
```

### Build from source (colcon)

```bash
cd ~/ros2_ws/src
git clone https://github.com/compas-rrc/compas_rrc_ros.git
cd ~/ros2_ws
colcon build --packages-select compas_rrc_driver
source install/setup.bash
```

### Launch driver

```bash
ros2 launch compas_rrc_driver bringup.launch.py robot_ip:=127.0.0.1 robot_streaming_port:=30101 robot_state_port:=30201
```

### Docker (ROS 2)

```bash
docker build --rm -f Dockerfile -t compasrrc/compas_rrc_driver:ros2 .
docker run --rm -it --net=host compasrrc/compas_rrc_driver:ros2
```

Inside the container:

```bash
ros2 launch compas_rrc_driver bringup.launch.py robot_ip:=127.0.0.1
```

For WSL scenarios:

```bash
ros2 launch compas_rrc_driver bringup_wsl.launch.py
```

## Launch parameters

* `robot_ip`: [*mandatory*] IP address of the robot.
* `robot_streaming_port`: [*optional*, `default=30101`] TCP port of the streaming interface of the robot.
* `robot_state_port`: [*optional*, `default=30201`] TCP port of the state interface of the robot.
* `sequence_check_mode`: [*optional*, `default=none`] Sequence check mode, valid options: `none`, `all`, `incoming`, `outgoing`.
* `namespace`: [*optional*, `default=''`] Namespace for running multiple driver instances.

## Protocol version (ROS 2)

The ROS 2 driver exposes a `get_protocol_version` service in its namespace
(e.g. `/rob1/get_protocol_version`). The Python client uses this service when
connecting via rosbridge.

## Notes on ROS 1 to ROS 2 migration

This package now uses the ROS 2 stack:

* `rclpy` node API instead of `rospy`.
* ROS 2 launch Python files (`*.launch.py`) instead of ROS 1 XML launch files.
* `ament_cmake` + `rosidl` interface generation instead of Catkin-specific message generation.

The `RobotMessage` topic and service interfaces remain in the package so existing higher-level command payloads stay compatible.

## License

This project is licensed under the terms of the [MIT License](/LICENSE).
