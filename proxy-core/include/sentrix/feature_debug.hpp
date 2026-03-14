#pragma once

#include <string>

#include "sentrix/detection_pipeline.hpp"
#include "sentrix/feature_mapping.hpp"
#include "sentrix/protocol_module.hpp"

namespace sentrix::featuredebug {

void appendComparison(
    const std::string& output_path,
    const ProtocolEvent& event,
    const RawFeatureVector& raw,
    const featuremap::FeatureComputation& features,
    const detection::DetectionResult& detection_result);

}  // namespace sentrix::featuredebug
