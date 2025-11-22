cmake_minimum_required(VERSION 3.10)
project(PoseGuardPro)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find packages
find_package(OpenCV REQUIRED)
find_package(dlib REQUIRED)
find_package(Qt6 COMPONENTS Widgets Multimedia REQUIRED)
find_package(nlohmann_json REQUIRED)

# Add executable
add_executable(PoseGuardPro main.cpp)

# Link libraries
target_link_libraries(PoseGuardPro PRIVATE
    ${OpenCV_LIBS}
    dlib::dlib
    Qt6::Widgets
    Qt6::Multimedia
    nlohmann_json::nlohmann_json
)

# Qt specific settings
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)