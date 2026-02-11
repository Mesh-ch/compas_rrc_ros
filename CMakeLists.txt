cmake_minimum_required(VERSION 3.8)
project(compas_rrc_driver)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/RobotMessage.msg"
  "srv/RobotMessageCommand.srv"
  "srv/RobotStringCommand.srv"
)

install(DIRECTORY
  src/compas_rrc_driver
  DESTINATION lib/${PROJECT_NAME}
)

install(PROGRAMS
  src/compas_rrc_driver/driver.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME driver
)

install(DIRECTORY
  launch
  DESTINATION share/${PROJECT_NAME}
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
