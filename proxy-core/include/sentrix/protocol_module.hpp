#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include "sentrix/feature_vector.hpp"

namespace sentrix {

struct ProtocolEvent {
    ProtocolKind protocol;
    std::vector<std::uint8_t> payload;
    std::string source_id;
};

struct RawFeatureVector {
    std::vector<float> values;
};

struct MitigationDecision {
    bool allow = true;
    std::string action = "forward";
    std::string reason;
};

class IProtocolModule {
public:
    virtual ~IProtocolModule() = default;

    virtual const char* name() const = 0;
    virtual void start() = 0;
    virtual void stop() = 0;

    virtual ProtocolEvent parse(const std::uint8_t* data, std::size_t len) = 0;
    virtual RawFeatureVector extractFeatures(const ProtocolEvent& event) = 0;
    virtual NormalizedFeatureVector normalize(const RawFeatureVector& raw) = 0;
    virtual void mitigate(const MitigationDecision& decision) = 0;
};

}  // namespace sentrix
