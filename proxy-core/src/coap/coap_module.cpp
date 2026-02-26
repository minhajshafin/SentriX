#include <algorithm>
#include <iostream>

#include "sentrix/coap_module.hpp"

namespace sentrix {

const char* CoapModule::name() const {
    return "coap";
}

void CoapModule::start() {
    std::cout << "[CoAP] module start (stub)" << std::endl;
}

void CoapModule::stop() {
    std::cout << "[CoAP] module stop (stub)" << std::endl;
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
