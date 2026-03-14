#pragma once

#include "sentrix/feature_vector.hpp"
#include "sentrix/protocol_module.hpp"

namespace sentrix::featuremap {

RawFeatureVector extractRawFeatures(const ProtocolEvent& event);
NormalizedFeatureVector normalizeFeatures(const RawFeatureVector& raw, ProtocolKind protocol);

}  // namespace sentrix::featuremap
