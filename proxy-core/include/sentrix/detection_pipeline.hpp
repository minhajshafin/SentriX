#pragma once

#include <atomic>
#include <string>
#include <vector>

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
    InferenceEngine();

    InferenceResult infer(const NormalizedFeatureVector& features, ProtocolKind protocol) const;
    bool usingOnnx() const;

private:
    float fallbackScore(const NormalizedFeatureVector& features, ProtocolKind protocol) const;
    float inferWithOnnx(const NormalizedFeatureVector& features) const;

    std::atomic<bool> onnx_ready_{false};
};

class MitigationEngine {
public:
    MitigationDecision decide(const RuleResult& rule, const InferenceResult& inference) const;
};

DetectionResult evaluate(const NormalizedFeatureVector& features, ProtocolKind protocol);

}  // namespace sentrix::detection
