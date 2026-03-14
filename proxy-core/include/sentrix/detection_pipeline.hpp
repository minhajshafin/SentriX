#pragma once

#include <string>

#include "sentrix/feature_vector.hpp"
#include "sentrix/protocol_module.hpp"

namespace sentrix::detection {

struct RuleResult {
    bool triggered = false;
    std::string reason;
};

struct InferenceResult {
    float anomaly_score = 0.0F;
    std::string predicted_label = "benign";
};

struct DetectionResult {
    RuleResult rule;
    InferenceResult inference;
    MitigationDecision decision;
};

class RuleEngine {
public:
    RuleResult evaluate(const NormalizedFeatureVector& features) const;
};

class InferenceEngine {
public:
    InferenceResult infer(const NormalizedFeatureVector& features, ProtocolKind protocol) const;
};

class MitigationEngine {
public:
    MitigationDecision decide(const RuleResult& rule, const InferenceResult& inference) const;
};

DetectionResult evaluate(const NormalizedFeatureVector& features, ProtocolKind protocol);

}  // namespace sentrix::detection
