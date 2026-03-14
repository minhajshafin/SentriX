#pragma once

#include "sentrix/feature_vector.hpp"
#include "sentrix/protocol_module.hpp"

namespace sentrix::featuremap {

struct FeatureComputation {
	NormalizedFeatureVector legacy{};
	NormalizedFeatureVector behavioral{};
	NormalizedFeatureVector active{};
	bool behavioral_enabled = false;
};

RawFeatureVector extractRawFeatures(const ProtocolEvent& event);
FeatureComputation computeFeatureVectors(const RawFeatureVector& raw, ProtocolKind protocol);
NormalizedFeatureVector normalizeFeatures(const RawFeatureVector& raw, ProtocolKind protocol);

}  // namespace sentrix::featuremap
