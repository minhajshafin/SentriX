cmake_minimum_required(VERSION 3.16)
project(sentrix_proxy LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(SENTRIX_ENABLE_ONNX_RUNTIME "Enable ONNX Runtime inference in detection pipeline" OFF)

add_executable(sentrix_proxy
    src/common/detection_pipeline.cpp
    src/common/event_log.cpp
    src/common/main.cpp
    src/common/metrics_store.cpp
    src/common/proxy_core.cpp
    src/mqtt/mqtt_module.cpp
    src/coap/coap_module.cpp
)

target_include_directories(sentrix_proxy PRIVATE include)

if(SENTRIX_ENABLE_ONNX_RUNTIME)
    target_compile_definitions(sentrix_proxy PRIVATE SENTRIX_ENABLE_ONNX_RUNTIME)

    find_path(ONNXRUNTIME_INCLUDE_DIR onnxruntime_cxx_api.h
        HINTS
            $ENV{ONNXRUNTIME_ROOT}/include
            /usr/include
            /usr/local/include)

    find_library(ONNXRUNTIME_LIBRARY onnxruntime
        HINTS
            $ENV{ONNXRUNTIME_ROOT}/lib
            /usr/lib
            /usr/local/lib)

    if(NOT ONNXRUNTIME_INCLUDE_DIR OR NOT ONNXRUNTIME_LIBRARY)
        message(FATAL_ERROR "SENTRIX_ENABLE_ONNX_RUNTIME=ON but ONNX Runtime not found. Set ONNXRUNTIME_ROOT or install onnxruntime dev package.")
    endif()

    target_include_directories(sentrix_proxy PRIVATE ${ONNXRUNTIME_INCLUDE_DIR})
    target_link_libraries(sentrix_proxy PRIVATE ${ONNXRUNTIME_LIBRARY})
endif()

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(sentrix_proxy PRIVATE -Wall -Wextra -Wpedantic)
endif()
