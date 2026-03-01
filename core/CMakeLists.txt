cmake_minimum_required(VERSION 3.20)
project(dsra1d_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(dsra1d_core STATIC
  src/version.cpp
)

target_include_directories(dsra1d_core PUBLIC include)
