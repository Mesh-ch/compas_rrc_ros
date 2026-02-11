cmake_minimum_required(VERSION 3.8)
project(compas_rrc_driver)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/RobotMessage.msg"
  "srv/GetProtocolVersion.srv"
  "srv/RobotMessageCommand.srv"
  "srv/RobotStringCommand.srv"
)

ament_get_python_install_dir(PYTHON_INSTALL_DIR)
install(DIRECTORY
  src/compas_rrc_driver/
  DESTINATION ${PYTHON_INSTALL_DIR}/compas_rrc_driver
  PATTERN "*.pyc" EXCLUDE
  PATTERN "__pycache__" EXCLUDE
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
