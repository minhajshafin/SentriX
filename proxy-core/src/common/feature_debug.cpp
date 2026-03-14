#include "sentrix/feature_debug.hpp"

#include <chrono>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <mutex>
#include <sstream>

namespace sentrix::featuredebug {

namespace {

std::mutex& debugMutex() {
    static std::mutex mutex;
    return mutex;
}

std::string nowIsoUtc() {
    const auto now = std::chrono::system_clock::now();
    const std::time_t now_time = std::chrono::system_clock::to_time_t(now);

    std::tm utc_tm{};
#if defined(_WIN32)
    gmtime_s(&utc_tm, &now_time);
#else
    gmtime_r(&now_time, &utc_tm);
#endif

    std::ostringstream oss;
    oss << std::put_time(&utc_tm, "%Y-%m-%dT%H:%M:%SZ");
    return oss.str();
}

std::string escapeJson(const std::string& input) {
    std::string output;
    output.reserve(input.size());

    for (const char c : input) {
        if (c == '\\') {
            output += "\\\\";
        } else if (c == '"') {
            output += "\\\"";
        } else if (c == '\n') {
            output += "\\n";
        } else {
            output += c;
        }
    }

    return output;
}

void writeVector(std::ostream& out, const NormalizedFeatureVector& values) {
    out << '[';
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i > 0) {
            out << ',';
        }
        out << values[i];
    }
    out << ']';
}

}  // namespace

void appendComparison(
    const std::string& output_path,
    const ProtocolEvent& event,
    const RawFeatureVector& raw,
    const featuremap::FeatureComputation& features,
    const detection::DetectionResult& detection_result) {
    if (output_path.empty()) {
        return;
    }

    std::lock_guard<std::mutex> lock(debugMutex());

    std::ofstream out(output_path, std::ios::app);
    if (!out.is_open()) {
        return;
    }

    out << '{';
    out << "\"ts\":\"" << nowIsoUtc() << "\",";
    out << "\"protocol\":\"" << (event.protocol == ProtocolKind::Mqtt ? "mqtt" : "coap") << "\",";
    out << "\"source_id\":\"" << escapeJson(event.source_id) << "\",";
    out << "\"direction\":\"" << escapeJson(event.direction) << "\",";
    out << "\"event_type\":\"" << escapeJson(event.event_type) << "\",";
    out << "\"detail\":\"" << escapeJson(event.detail) << "\",";
    out << "\"raw_bytes\":" << (raw.values.empty() ? 0.0F : raw.values[0]) << ',';
    out << "\"behavioral_enabled\":" << (features.behavioral_enabled ? "true" : "false") << ',';
    out << "\"legacy\":";
    writeVector(out, features.legacy);
    out << ',';
    out << "\"behavioral\":";
    writeVector(out, features.behavioral);
    out << ',';
    out << "\"active\":";
    writeVector(out, features.active);
    out << ',';
    out << "\"decision\":{"
        << "\"allow\":" << (detection_result.decision.allow ? "true" : "false") << ','
        << "\"action\":\"" << escapeJson(detection_result.decision.action) << "\"," 
        << "\"reason\":\"" << escapeJson(detection_result.decision.reason) << "\"," 
        << "\"anomaly_score\":" << detection_result.inference.anomaly_score
        << '}';
    out << "}" << '\n';
}

}  // namespace sentrix::featuredebug
