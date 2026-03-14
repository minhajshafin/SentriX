#include "sentrix/detection_pipeline.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <memory>
#include <mutex>
#include <vector>

#ifdef SENTRIX_ENABLE_ONNX_RUNTIME
#include <onnxruntime_cxx_api.h>
#endif

namespace sentrix::detection {

namespace {

constexpr std::size_t kMsgRateIndex = 0;
constexpr std::size_t kPayloadSizeIndex = 2;

constexpr float kMsgRateRuleThreshold = 0.95F;
constexpr float kPayloadSizeRuleThreshold = 0.97F;
constexpr float kInferenceDropThreshold = 0.90F;
constexpr float kInferenceRateLimitThreshold = 0.75F;
constexpr char kOnnxModelPathEnv[] = "SENTRIX_ONNX_MODEL_PATH";

#ifdef SENTRIX_ENABLE_ONNX_RUNTIME
struct OnnxRuntimeState {
    bool initialized = false;
    bool available = false;
    std::string model_path;
    std::string error;
    std::string input_name;
    std::vector<std::string> output_names;
    std::vector<const char*> output_name_ptrs;
    std::unique_ptr<Ort::Env> env;
    std::unique_ptr<Ort::Session> session;
};

OnnxRuntimeState& onnxState() {
    static OnnxRuntimeState state;
    static std::mutex init_mutex;

    std::lock_guard<std::mutex> lock(init_mutex);
    if (state.initialized) {
        return state;
    }

    state.initialized = true;
    const char* model_path = std::getenv(kOnnxModelPathEnv);
    if (model_path == nullptr || *model_path == '\0') {
        state.error = "env SENTRIX_ONNX_MODEL_PATH not set";
        return state;
    }

    state.model_path = model_path;
    if (!std::filesystem::exists(state.model_path)) {
        state.error = "model file not found";
        return state;
    }

    try {
        state.env = std::make_unique<Ort::Env>(ORT_LOGGING_LEVEL_WARNING, "sentrix");

        Ort::SessionOptions session_options;
        session_options.SetIntraOpNumThreads(1);
        session_options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_BASIC);

        state.session = std::make_unique<Ort::Session>(*state.env, state.model_path.c_str(), session_options);

        Ort::AllocatorWithDefaultOptions allocator;
        auto input_name_alloc = state.session->GetInputNameAllocated(0, allocator);
        state.input_name = input_name_alloc.get();

        const std::size_t output_count = state.session->GetOutputCount();
        state.output_names.reserve(output_count);
        state.output_name_ptrs.reserve(output_count);
        for (std::size_t i = 0; i < output_count; ++i) {
            auto output_name_alloc = state.session->GetOutputNameAllocated(i, allocator);
            state.output_names.emplace_back(output_name_alloc.get());
        }

        for (const auto& name : state.output_names) {
            state.output_name_ptrs.push_back(name.c_str());
        }

        state.available = true;
        std::cout << "[Detection] ONNX runtime enabled with model: " << state.model_path << std::endl;
    } catch (const Ort::Exception& ex) {
        state.error = ex.what();
        state.available = false;
    }

    return state;
}

float scoreFromTensorOutput(const Ort::Value& output) {
    if (!output.IsTensor()) {
        return -1.0F;
    }

    const auto type_info = output.GetTensorTypeAndShapeInfo();
    if (type_info.GetElementType() != ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT) {
        return -1.0F;
    }

    const std::size_t count = type_info.GetElementCount();
    if (count == 0) {
        return 0.0F;
    }

    const float* raw = output.GetTensorData<float>();
    const float max_value = *std::max_element(raw, raw + count);

    bool bounded = true;
    for (std::size_t i = 0; i < count; ++i) {
        bounded = bounded && raw[i] >= 0.0F && raw[i] <= 1.0F;
    }

    if (bounded) {
        return std::clamp(max_value, 0.0F, 1.0F);
    }

    // Treat as logits and map to [0,1] with sigmoid on max logit.
    const float sigmoid = 1.0F / (1.0F + std::exp(-max_value));
    return std::clamp(sigmoid, 0.0F, 1.0F);
}
#endif

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

    if (usingOnnx()) {
        const float onnx_score = inferWithOnnx(features);
        if (onnx_score >= 0.0F) {
            result.anomaly_score = onnx_score;
            result.predicted_label = result.anomaly_score >= 0.5F ? "suspicious" : "benign";
            return result;
        }
    }

    result.anomaly_score = fallbackScore(features, protocol);
    result.predicted_label = result.anomaly_score >= 0.5F ? "suspicious" : "benign";
    return result;
}

InferenceEngine::InferenceEngine() {
#ifdef SENTRIX_ENABLE_ONNX_RUNTIME
    const auto& state = onnxState();
    onnx_ready_.store(state.available, std::memory_order_relaxed);
    if (!state.available && !state.error.empty()) {
        std::cerr << "[Detection] ONNX unavailable, fallback heuristic active: " << state.error << std::endl;
    }
#else
    onnx_ready_.store(false, std::memory_order_relaxed);
#endif
}

bool InferenceEngine::usingOnnx() const {
    return onnx_ready_.load(std::memory_order_relaxed);
}

float InferenceEngine::fallbackScore(const NormalizedFeatureVector& features, ProtocolKind protocol) const {

    const float payload_size = features[kPayloadSizeIndex];
    const float msg_rate = features[kMsgRateIndex];

    // Week 7 scaffolding heuristic: combines burstiness and payload pressure.
    float score = 0.65F * msg_rate + 0.35F * payload_size;
    if (protocol == ProtocolKind::Coap) {
        score = std::min(1.0F, score + 0.03F);
    }

    return std::clamp(score, 0.0F, 1.0F);
}

float InferenceEngine::inferWithOnnx(const NormalizedFeatureVector& features) const {
#ifdef SENTRIX_ENABLE_ONNX_RUNTIME
    auto& state = onnxState();
    if (!state.available || !state.session) {
        return -1.0F;
    }

    const std::array<std::int64_t, 2> input_shape{
        1,
        static_cast<std::int64_t>(kTotalFeatureDims),
    };
    std::vector<float> input(features.begin(), features.end());

    Ort::MemoryInfo memory_info = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
    Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
        memory_info,
        input.data(),
        input.size(),
        input_shape.data(),
        input_shape.size());

    const char* input_names[] = {state.input_name.c_str()};
    auto outputs = state.session->Run(
        Ort::RunOptions{nullptr},
        input_names,
        &input_tensor,
        1,
        state.output_name_ptrs.data(),
        state.output_name_ptrs.size());

    if (outputs.empty()) {
        return -1.0F;
    }

    return scoreFromTensorOutput(outputs.front());
#else
    (void)features;
    return -1.0F;
#endif
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
