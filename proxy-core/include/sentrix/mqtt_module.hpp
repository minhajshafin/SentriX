#pragma once

#include "sentrix/protocol_module.hpp"

namespace sentrix {

class MqttModule final : public IProtocolModule {
public:
    const char* name() const override;
    void start() override;
    void stop() override;

    ProtocolEvent parse(const std::uint8_t* data, std::size_t len) override;
    RawFeatureVector extractFeatures(const ProtocolEvent& event) override;
    NormalizedFeatureVector normalize(const RawFeatureVector& raw) override;
    void mitigate(const MitigationDecision& decision) override;
};

}  // namespace sentrix
