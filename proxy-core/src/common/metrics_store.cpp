#include "sentrix/metrics_store.hpp"

#include <atomic>
#include <cstdint>
#include <fstream>

namespace sentrix::metrics {

namespace {

std::atomic<std::size_t> g_mqtt_messages{0};
std::atomic<std::size_t> g_coap_messages{0};
std::atomic<std::size_t> g_detections{0};
std::atomic<std::size_t> g_latency_p95_ms{0};

}  // namespace

void addMqttMessages(std::size_t count) {
    g_mqtt_messages.fetch_add(count, std::memory_order_relaxed);
}

void addCoapMessages(std::size_t count) {
    g_coap_messages.fetch_add(count, std::memory_order_relaxed);
}

void setDetections(std::size_t count) {
    g_detections.store(count, std::memory_order_relaxed);
}

void setLatencyP95Ms(std::size_t value) {
    g_latency_p95_ms.store(value, std::memory_order_relaxed);
}

std::size_t mqttMessages() {
    return g_mqtt_messages.load(std::memory_order_relaxed);
}

std::size_t coapMessages() {
    return g_coap_messages.load(std::memory_order_relaxed);
}

std::size_t detections() {
    return g_detections.load(std::memory_order_relaxed);
}

std::size_t latencyP95Ms() {
    return g_latency_p95_ms.load(std::memory_order_relaxed);
}

bool writeSnapshot(const std::string& output_path) {
    std::ofstream out(output_path, std::ios::trunc);
    if (!out.is_open()) {
        return false;
    }

    out << "{";
    out << "\"mqtt_msgs\":" << mqttMessages() << ',';
    out << "\"coap_msgs\":" << coapMessages() << ',';
    out << "\"detections\":" << detections() << ',';
    out << "\"latency_ms_p95\":" << latencyP95Ms();
    out << "}";
    out.flush();

    return static_cast<bool>(out);
}

}  // namespace sentrix::metrics
