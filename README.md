# COMPAS RRC: ROS 2 driver

![COMPAS RRC](images/compas_rrc.png)

> ROS 2 package for the COMPAS RRC driver for ABB robots.

## ROS 2 Usage

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

For WSL scenarios:

```bash
ros2 launch compas_rrc_driver bringup_wsl.launch.py
```

## Launch parameters

* `robot_ip`: [*mandatory*] IP address of the robot.
* `robot_streaming_port`: [*optional*, `default=30101`] TCP port of the streaming interface of the robot.
* `robot_state_port`: [*optional*, `default=30201`] TCP port of the state interface of the robot.
* `sequence_check_mode`: [*optional*, `default=none`] Sequence check mode, valid options: `none`, `all`, `incoming`, `outgoing`.
* `namespace`: [*optional*, `default='rob1'`] Namespace for running multiple driver instances.

## Notes on ROS 1 to ROS 2 migration

This package now uses the ROS 2 stack:

* `rclpy` node API instead of `rospy`.
* ROS 2 launch Python files (`*.launch.py`) instead of ROS 1 XML launch files.
* `ament_cmake` + `rosidl` interface generation instead of Catkin-specific message generation.

The `RobotMessage` topic and service interfaces remain in the package so existing higher-level command payloads stay compatible.

## License

This project is licensed under the terms of the [MIT License](/LICENSE).
