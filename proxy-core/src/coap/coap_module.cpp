#include <algorithm>
#include <cstdlib>
#include <iostream>

#include "sentrix/coap_module.hpp"
#include "sentrix/event_log.hpp"

namespace sentrix {

const char* CoapModule::name() const {
    return "coap";
}

void CoapModule::start() {
    std::cout << "[CoAP] module start (stub)" << std::endl;
    const char* path = std::getenv("SENTRIX_EVENTS_PATH");
    eventlog::appendEvent(path != nullptr ? path : "/tmp/sentrix_events.log", "coap", "internal", "module_start", 0, "stub module online");
}

void CoapModule::stop() {
    std::cout << "[CoAP] module stop (stub)" << std::endl;
    const char* path = std::getenv("SENTRIX_EVENTS_PATH");
    eventlog::appendEvent(path != nullptr ? path : "/tmp/sentrix_events.log", "coap", "internal", "module_stop", 0, "stub module stopped");
}

ProtocolEvent CoapModule::parse(const std::uint8_t* data, std::size_t len) {
    ProtocolEvent event{};
    event.protocol = ProtocolKind::Coap;
    event.source_id = "coap-source";
    event.payload.assign(data, data + len);
    return event;
}

RawFeatureVector CoapModule::extractFeatures(const ProtocolEvent& event) {
    RawFeatureVector features{};
    features.values = {
        static_cast<float>(event.payload.size()),
        static_cast<float>(event.source_id.size()),
    };
    return features;
}

NormalizedFeatureVector CoapModule::normalize(const RawFeatureVector& raw) {
    NormalizedFeatureVector normalized{};
    normalized.fill(0.0F);

    if (!raw.values.empty()) {
        normalized[2] = std::min(raw.values[0] / 1024.0F, 1.0F);
    }

    normalized[15] = 0.0F;
    normalized[16] = 1.0F;
    return normalized;
}

void CoapModule::mitigate(const MitigationDecision& decision) {
    std::cout << "[CoAP] mitigation action=" << decision.action
              << " allow=" << (decision.allow ? "true" : "false") << std::endl;
}

}  // namespace sentrix
