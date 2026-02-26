cmake_minimum_required(VERSION 3.16)
project(sentrix_proxy LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(sentrix_proxy
    src/common/event_log.cpp
    src/common/main.cpp
    src/common/metrics_store.cpp
    src/common/proxy_core.cpp
    src/mqtt/mqtt_module.cpp
    src/coap/coap_module.cpp
)

target_include_directories(sentrix_proxy PRIVATE include)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(sentrix_proxy PRIVATE -Wall -Wextra -Wpedantic)
endif()
