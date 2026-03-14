cmake_minimum_required(VERSION 3.16)
project(sentrix_proxy LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(SENTRIX_ENABLE_ONNX_RUNTIME "Enable ONNX Runtime inference in detection pipeline" OFF)

add_executable(sentrix_proxy
    src/common/detection_pipeline.cpp
    src/common/event_log.cpp
    src/common/feature_mapping.cpp
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
            ${CMAKE_SOURCE_DIR}/third_party/onnxruntime/include
            /usr/include
            /usr/local/include)

    if(NOT ONNXRUNTIME_INCLUDE_DIR)
        find_path(ONNXRUNTIME_INCLUDE_DIR onnxruntime_cxx_api.h
            HINTS
                $ENV{ONNXRUNTIME_ROOT}/include
                ${CMAKE_SOURCE_DIR}/third_party/onnxruntime/include
                /usr/include
                /usr/local/include
            PATH_SUFFIXES
                onnxruntime/core/session)
    endif()

    find_library(ONNXRUNTIME_LIBRARY onnxruntime
        HINTS
            $ENV{ONNXRUNTIME_ROOT}/lib
            ${CMAKE_SOURCE_DIR}/third_party/onnxruntime/lib
            /usr/lib
            /usr/local/lib)

    if(NOT ONNXRUNTIME_LIBRARY)
        find_file(ONNXRUNTIME_LIBRARY_FILE
            NAMES
                libonnxruntime.so
                libonnxruntime.so.1
                libonnxruntime.so.1.24.3
            HINTS
                $ENV{ONNXRUNTIME_ROOT}/lib
                ${CMAKE_SOURCE_DIR}/third_party/onnxruntime/lib
                /usr/lib
                /usr/local/lib)
        if(ONNXRUNTIME_LIBRARY_FILE)
            set(ONNXRUNTIME_LIBRARY ${ONNXRUNTIME_LIBRARY_FILE})
        endif()
    endif()

    if(NOT ONNXRUNTIME_INCLUDE_DIR OR NOT ONNXRUNTIME_LIBRARY)
        message(FATAL_ERROR "SENTRIX_ENABLE_ONNX_RUNTIME=ON but ONNX Runtime C++ SDK not found. Set ONNXRUNTIME_ROOT to an SDK path containing include/ and lib/, or place SDK under proxy-core/third_party/onnxruntime.")
    endif()

    target_include_directories(sentrix_proxy PRIVATE ${ONNXRUNTIME_INCLUDE_DIR})
    target_link_libraries(sentrix_proxy PRIVATE ${ONNXRUNTIME_LIBRARY})
endif()

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(sentrix_proxy PRIVATE -Wall -Wextra -Wpedantic)
endif()
