# config file for arduino-cmake. for instructions, see:
# https://github.com/queezythegreat/arduino-cmake#using-arduino-cmake

# Path to your arduino-cmake directory
set(CMAKE_ARDUINO_PATH ./arduino-cmake)
set(CMAKE_TOOLCHAIN_FILE ${CMAKE_ARDUINO_PATH}/cmake/ArduinoToolchain.cmake) 

# Set the minimum required version of cmake for your project
cmake_minimum_required(VERSION 2.8)

set(PROJECT_NAME controller)

# Define your project and language
project(${PROJECT_NAME} C CXX)

generate_arduino_firmware(${PROJECT_NAME}
  SRCS controller.cpp Sensors/Sensors.cpp Sensors/LSM303/LSM303.cpp Sensors/L3G4200D/L3G4200D.cpp
  BOARD uno
  PORT /dev/ttyACM0)
