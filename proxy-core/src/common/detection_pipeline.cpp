#include "sentrix/detection_pipeline.hpp"

#include <algorithm>

namespace sentrix::detection {

namespace {

constexpr std::size_t kMsgRateIndex = 0;
constexpr std::size_t kPayloadSizeIndex = 2;

constexpr float kMsgRateRuleThreshold = 0.95F;
constexpr float kPayloadSizeRuleThreshold = 0.97F;
constexpr float kInferenceDropThreshold = 0.90F;
constexpr float kInferenceRateLimitThreshold = 0.75F;

}  // namespace

RuleResult RuleEngine::evaluate(const NormalizedFeatureVector& features) const {
    RuleResult result{};

    const float msg_rate = features[kMsgRateIndex];
    const float payload_size = features[kPayloadSizeIndex];

    if (msg_rate >= kMsgRateRuleThreshold) {
        result.triggered = true;
        result.reason = "rule:msg_rate_exceeded";
        return result;
    }

    if (payload_size >= kPayloadSizeRuleThreshold) {
        result.triggered = true;
        result.reason = "rule:oversized_payload";
    }

    return result;
}

InferenceResult InferenceEngine::infer(const NormalizedFeatureVector& features, ProtocolKind protocol) const {
    InferenceResult result{};

    const float payload_size = features[kPayloadSizeIndex];
    const float msg_rate = features[kMsgRateIndex];

    // Week 7 scaffolding heuristic: combines burstiness and payload pressure.
    float score = 0.65F * msg_rate + 0.35F * payload_size;
    if (protocol == ProtocolKind::Coap) {
        score = std::min(1.0F, score + 0.03F);
    }

    result.anomaly_score = std::clamp(score, 0.0F, 1.0F);
    result.predicted_label = result.anomaly_score >= 0.5F ? "suspicious" : "benign";
    return result;
}

MitigationDecision MitigationEngine::decide(const RuleResult& rule, const InferenceResult& inference) const {
    MitigationDecision decision{};
    decision.allow = true;
    decision.action = "forward";

    if (rule.triggered) {
        decision.allow = false;
        decision.action = "drop";
        decision.reason = rule.reason;
        return decision;
    }

    if (inference.anomaly_score >= kInferenceDropThreshold) {
        decision.allow = false;
        decision.action = "drop";
        decision.reason = "inference:high_anomaly_score";
        return decision;
    }

    if (inference.anomaly_score >= kInferenceRateLimitThreshold) {
        decision.allow = true;
        decision.action = "rate_limit";
        decision.reason = "inference:elevated_anomaly_score";
    }

    return decision;
}

DetectionResult evaluate(const NormalizedFeatureVector& features, ProtocolKind protocol) {
    static const RuleEngine rule_engine;
    static const InferenceEngine inference_engine;
    static const MitigationEngine mitigation_engine;

    DetectionResult out{};
    out.rule = rule_engine.evaluate(features);
    out.inference = inference_engine.infer(features, protocol);
    out.decision = mitigation_engine.decide(out.rule, out.inference);
    return out;
}

}  // namespace sentrix::detection
