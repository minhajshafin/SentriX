#pragma once

#include <cstddef>
#include <string>

namespace sentrix::metrics {

void addMqttMessages(std::size_t count);
void addCoapMessages(std::size_t count);
void addDetections(std::size_t count);
void setDetections(std::size_t count);
void setLatencyP95Ms(std::size_t value);

std::size_t mqttMessages();
std::size_t coapMessages();
std::size_t detections();
std::size_t latencyP95Ms();

bool writeSnapshot(const std::string& output_path);

}  // namespace sentrix::metrics
