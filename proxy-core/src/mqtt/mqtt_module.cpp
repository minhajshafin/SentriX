#include <algorithm>
#include <iostream>

#include "sentrix/mqtt_module.hpp"

namespace sentrix {

const char* MqttModule::name() const {
    return "mqtt";
}

void MqttModule::start() {
    std::cout << "[MQTT] module start (stub)" << std::endl;
}

void MqttModule::stop() {
    std::cout << "[MQTT] module stop (stub)" << std::endl;
}

ProtocolEvent MqttModule::parse(const std::uint8_t* data, std::size_t len) {
    ProtocolEvent event{};
    event.protocol = ProtocolKind::Mqtt;
    event.source_id = "mqtt-client";
    event.payload.assign(data, data + len);
    return event;
}

RawFeatureVector MqttModule::extractFeatures(const ProtocolEvent& event) {
    RawFeatureVector features{};
    features.values = {
        static_cast<float>(event.payload.size()),
        static_cast<float>(event.source_id.size()),
    };
    return features;
}

NormalizedFeatureVector MqttModule::normalize(const RawFeatureVector& raw) {
    NormalizedFeatureVector normalized{};
    normalized.fill(0.0F);

    if (!raw.values.empty()) {
        normalized[2] = std::min(raw.values[0] / 1024.0F, 1.0F);
    }

    normalized[15] = 1.0F;
    normalized[16] = 0.0F;
    return normalized;
}

void MqttModule::mitigate(const MitigationDecision& decision) {
    std::cout << "[MQTT] mitigation action=" << decision.action
              << " allow=" << (decision.allow ? "true" : "false") << std::endl;
}

}  // namespace sentrix
