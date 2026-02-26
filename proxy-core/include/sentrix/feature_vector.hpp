#pragma once

#include <array>
#include <cstdint>

namespace sentrix {

constexpr std::size_t kNormalizedFeatureDims = 15;
constexpr std::size_t kProtocolIdDims = 2;
constexpr std::size_t kMqttAuxDims = 8;
constexpr std::size_t kCoapAuxDims = 8;
constexpr std::size_t kTotalFeatureDims =
    kNormalizedFeatureDims + kProtocolIdDims + kMqttAuxDims + kCoapAuxDims;

using NormalizedFeatureVector = std::array<float, kTotalFeatureDims>;

enum class ProtocolKind : std::uint8_t {
    Mqtt = 0,
    Coap = 1,
};

}  // namespace sentrix
