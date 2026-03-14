#include "sentrix/feature_mapping.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <deque>
#include <mutex>
#include <sstream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace sentrix::featuremap {

namespace {

using Clock = std::chrono::steady_clock;

constexpr char kBehavioralWindowsEnv[] = "SENTRIX_ENABLE_BEHAVIORAL_WINDOWS";
constexpr auto kMsgRateWindow = std::chrono::seconds(1);
constexpr auto kShortWindow = std::chrono::seconds(10);
constexpr auto kLongWindow = std::chrono::seconds(30);
constexpr float kInterArrivalCapMs = 1000.0F;
constexpr float kPathEntropyCap = 4.0F;
constexpr float kPayloadToResourceCap = 64.0F;

struct TimedFloat {
    Clock::time_point ts;
    float value;
};

struct TimedString {
    Clock::time_point ts;
    std::string value;
};

struct SourceWindowState {
    bool initialized = false;
    Clock::time_point session_start{};
    Clock::time_point last_seen{};
    std::deque<Clock::time_point> message_times;
    std::deque<TimedString> resources;
    std::deque<TimedFloat> error_flags;
    std::deque<TimedFloat> handshake_flags;
    std::deque<Clock::time_point> reconnects;
    std::deque<Clock::time_point> breadth_events;
    std::deque<TimedFloat> message_sizes;
    std::deque<TimedString> coap_types;
    std::deque<TimedFloat> option_counts;
};

std::mutex& stateMutex() {
    static std::mutex mutex;
    return mutex;
}

std::unordered_map<std::string, SourceWindowState>& stateMap() {
    static std::unordered_map<std::string, SourceWindowState> states;
    return states;
}

float clamp01(float value) {
    return std::max(0.0F, std::min(value, 1.0F));
}

float norm(float value, float cap) {
    if (cap <= 0.0F) {
        return 0.0F;
    }
    return clamp01(value / cap);
}

bool contains(const std::string& haystack, const std::string& needle) {
    return haystack.find(needle) != std::string::npos;
}

bool envEnabled(const char* name) {
    const char* value = std::getenv(name);
    if (value == nullptr) {
        return false;
    }
    const std::string normalized(value);
    return normalized == "1" || normalized == "true" || normalized == "TRUE" || normalized == "yes";
}

std::string extractTaggedValue(const std::string& detail, const std::string& key) {
    const std::size_t start = detail.find(key);
    if (start == std::string::npos) {
        return {};
    }

    const std::size_t value_start = start + key.size();
    const std::size_t value_end = detail.find('|', value_start);
    if (value_end == std::string::npos) {
        return detail.substr(value_start);
    }
    return detail.substr(value_start, value_end - value_start);
}

float shannonEntropy(const std::vector<std::uint8_t>& bytes) {
    if (bytes.empty()) {
        return 0.0F;
    }

    std::array<std::size_t, 256> counts{};
    counts.fill(0);
    for (std::uint8_t byte : bytes) {
        ++counts[byte];
    }

    const float total = static_cast<float>(bytes.size());
    float entropy = 0.0F;
    for (std::size_t count : counts) {
        if (count == 0) {
            continue;
        }
        const float probability = static_cast<float>(count) / total;
        entropy -= probability * std::log2(probability);
    }
    return entropy;
}

float stringEntropy(const std::string& value) {
    if (value.empty()) {
        return 0.0F;
    }

    std::unordered_map<char, std::size_t> counts;
    for (char ch : value) {
        ++counts[ch];
    }

    const float total = static_cast<float>(value.size());
    float entropy = 0.0F;
    for (const auto& [_, count] : counts) {
        const float probability = static_cast<float>(count) / total;
        entropy -= probability * std::log2(probability);
    }
    return entropy;
}

void pruneTimes(std::deque<Clock::time_point>& values, Clock::time_point now, Clock::duration window) {
    while (!values.empty() && (now - values.front()) > window) {
        values.pop_front();
    }
}

void pruneTimedFloats(std::deque<TimedFloat>& values, Clock::time_point now, Clock::duration window) {
    while (!values.empty() && (now - values.front().ts) > window) {
        values.pop_front();
    }
}

void pruneTimedStrings(std::deque<TimedString>& values, Clock::time_point now, Clock::duration window) {
    while (!values.empty() && (now - values.front().ts) > window) {
        values.pop_front();
    }
}

float averageTimedFloat(const std::deque<TimedFloat>& values) {
    if (values.empty()) {
        return 0.0F;
    }
    float sum = 0.0F;
    for (const auto& item : values) {
        sum += item.value;
    }
    return sum / static_cast<float>(values.size());
}

float varianceTimedFloat(const std::deque<TimedFloat>& values) {
    if (values.size() < 2) {
        return 0.0F;
    }
    const float mean = averageTimedFloat(values);
    float sum = 0.0F;
    for (const auto& item : values) {
        const float delta = item.value - mean;
        sum += delta * delta;
    }
    return sum / static_cast<float>(values.size());
}

std::size_t uniqueRecentResources(const std::deque<TimedString>& resources) {
    std::unordered_set<std::string> unique;
    for (const auto& item : resources) {
        if (!item.value.empty()) {
            unique.insert(item.value);
        }
    }
    return unique.size();
}

float normalizedResourceDepth(const std::string& resource) {
    if (resource.empty()) {
        return 0.0F;
    }
    std::size_t depth = 1;
    for (char ch : resource) {
        if (ch == '/') {
            ++depth;
        }
    }
    return norm(static_cast<float>(depth), 8.0F);
}

float sourceIdEntropy(const std::string& source_id) {
    return clamp01(stringEntropy(source_id) / kPathEntropyCap);
}

NormalizedFeatureVector legacyNormalize(const RawFeatureVector& raw, ProtocolKind protocol) {
    NormalizedFeatureVector out{};
    out.fill(0.0F);

    const float byte_count = raw.values.empty() ? 0.0F : raw.values[0];
    const bool is_mqtt = protocol == ProtocolKind::Mqtt;
    const bool is_traffic = raw.event_type == "traffic";
    const bool has_error_or_abuse = contains(raw.detail, "error") || contains(raw.detail, "abuse");
    const bool has_malform = contains(raw.detail, "malform");
    const bool has_wildcard = contains(raw.detail, "wildcard");
    const bool is_connection_open = raw.event_type == "connection_open";
    const bool is_outgoing = raw.direction == "outgoing";
    const bool is_con = contains(raw.detail, "con");

    const float msg_rate = is_traffic ? 1.0F : 0.2F;
    const float inter_arrival = 0.5F;
    const float payload_size = norm(std::log1p(std::max(byte_count, 0.0F)), std::log1p(4096.0F));
    const float payload_entropy = byte_count > 0.0F ? 0.5F : 0.0F;

    float resource_depth = 0.0F;
    float resource_entropy = 0.0F;
    float qos_level = 0.0F;
    float session_duration = 0.0F;
    float unique_resource_count = 0.0F;
    float error_rate = 0.0F;
    float handshake_complexity = 0.0F;
    float subscription_breadth = 0.0F;
    float reconnection_rate = 0.0F;
    float payload_to_resource_ratio = 0.0F;
    float compliance = 0.0F;
    std::array<float, 8> aux{};
    aux.fill(0.0F);

    if (is_mqtt) {
        resource_depth = 0.25F;
        resource_entropy = 0.45F;
        qos_level = 0.5F;
        session_duration = 0.5F;
        unique_resource_count = 0.2F;
        error_rate = has_error_or_abuse ? 0.6F : 0.05F;
        handshake_complexity = is_connection_open ? 0.6F : 0.2F;
        subscription_breadth = has_wildcard ? 0.7F : 0.15F;
        reconnection_rate = is_connection_open ? 0.8F : 0.2F;
        payload_to_resource_ratio = norm(byte_count / 20.0F, 50.0F);
        compliance = has_malform ? 0.3F : 0.95F;
        aux = {
            0.0F,
            has_wildcard ? 1.0F : 0.0F,
            is_connection_open ? 1.0F : 0.2F,
            0.6F,
            0.0F,
            0.2F,
            0.5F,
            norm(byte_count, 2048.0F),
        };
    } else {
        resource_depth = 0.3F;
        resource_entropy = 0.5F;
        qos_level = is_con ? 1.0F : 0.0F;
        session_duration = 0.3F;
        unique_resource_count = 0.25F;
        error_rate = has_error_or_abuse ? 0.6F : 0.05F;
        handshake_complexity = is_outgoing ? 0.6F : 0.2F;
        subscription_breadth = 0.4F;
        reconnection_rate = 0.3F;
        payload_to_resource_ratio = norm(byte_count / 16.0F, 64.0F);
        compliance = has_malform ? 0.3F : 0.95F;
    }

    const std::array<float, kNormalizedFeatureDims> normalized = {
        msg_rate,
        inter_arrival,
        payload_size,
        payload_entropy,
        resource_depth,
        resource_entropy,
        qos_level,
        session_duration,
        unique_resource_count,
        error_rate,
        handshake_complexity,
        subscription_breadth,
        reconnection_rate,
        payload_to_resource_ratio,
        compliance,
    };

    for (std::size_t i = 0; i < normalized.size(); ++i) {
        out[i] = normalized[i];
    }

    out[15] = is_mqtt ? 1.0F : 0.0F;
    out[16] = is_mqtt ? 0.0F : 1.0F;

    if (is_mqtt) {
        for (std::size_t i = 0; i < aux.size(); ++i) {
            out[17 + i] = aux[i];
        }
    }

    return out;
}

NormalizedFeatureVector statefulNormalize(const RawFeatureVector& raw, ProtocolKind protocol) {
    const bool is_mqtt = protocol == ProtocolKind::Mqtt;
    const float byte_count = raw.values.empty() ? 0.0F : raw.values[0];
    const float payload_entropy_bits = raw.values.size() > 2 ? raw.values[2] : 0.0F;
    const std::string resource = [&]() {
        std::string topic = extractTaggedValue(raw.detail, "topic:");
        if (!topic.empty()) {
            return topic;
        }
        std::string path = extractTaggedValue(raw.detail, "path:");
        return path;
    }();
    const bool has_error = contains(raw.detail, "error") || contains(raw.detail, "abuse") || contains(raw.detail, "malform");
    const bool breadth_event = contains(raw.detail, "wildcard") || contains(raw.detail, "observe");
    const bool reconnect_event = raw.event_type == "connection_open";
    const bool is_con = contains(raw.detail, "|con|") || contains(raw.detail, "|con") || contains(raw.detail, "con|");
    const bool is_non = contains(raw.detail, "|non|") || contains(raw.detail, "|non") || contains(raw.detail, "non|");
    const bool is_ack = contains(raw.detail, "|ack|") || contains(raw.detail, "|ack") || contains(raw.detail, "ack|");
    const bool is_rst = contains(raw.detail, "|rst|") || contains(raw.detail, "|rst") || contains(raw.detail, "rst|");
    const bool is_handshake = reconnect_event || contains(raw.detail, "pubrec") || contains(raw.detail, "pubrel") ||
                              contains(raw.detail, "pubcomp") || is_ack || is_con;
    const float option_count = [&]() {
        const std::string value = extractTaggedValue(raw.detail, "optcount:");
        if (value.empty()) {
            return 0.0F;
        }
        try {
            return std::stof(value);
        } catch (...) {
            return 0.0F;
        }
    }();

    const Clock::time_point now = Clock::now();
    const std::string state_key = (is_mqtt ? "mqtt:" : "coap:") + raw.source_id;

    float inter_arrival_ms = kInterArrivalCapMs;
    std::size_t unique_resource_count = 0;
    float session_seconds = 0.0F;
    float error_rate = 0.0F;
    float handshake_complexity = 0.0F;
    float subscription_breadth = 0.0F;
    float reconnection_rate = 0.0F;
    float message_size_variance = 0.0F;
    float msg_count_window = 1.0F;
    float con_ratio = 0.0F;
    float non_ratio = 0.0F;
    float ack_ratio = 0.0F;
    float rst_ratio = 0.0F;
    float mean_option_count = 0.0F;

    {
        std::lock_guard<std::mutex> lock(stateMutex());
        auto& state = stateMap()[state_key];
        if (!state.initialized) {
            state.initialized = true;
            state.session_start = now;
            state.last_seen = now;
        } else {
            inter_arrival_ms = std::chrono::duration_cast<std::chrono::milliseconds>(now - state.last_seen).count();
            state.last_seen = now;
        }

        if (reconnect_event) {
            state.reconnects.push_back(now);
            state.session_start = now;
        }

        state.message_times.push_back(now);
        state.message_sizes.push_back({now, byte_count});
        state.error_flags.push_back({now, has_error ? 1.0F : 0.0F});
        state.handshake_flags.push_back({now, is_handshake ? 1.0F : 0.0F});

        if (!resource.empty()) {
            state.resources.push_back({now, resource});
        }
        if (breadth_event) {
            state.breadth_events.push_back(now);
        }
        if (!is_mqtt) {
            if (is_con) {
                state.coap_types.push_back({now, "con"});
            } else if (is_non) {
                state.coap_types.push_back({now, "non"});
            } else if (is_ack) {
                state.coap_types.push_back({now, "ack"});
            } else if (is_rst) {
                state.coap_types.push_back({now, "rst"});
            }
            state.option_counts.push_back({now, option_count});
        }

        pruneTimes(state.message_times, now, kMsgRateWindow);
        pruneTimedStrings(state.resources, now, kShortWindow);
        pruneTimedFloats(state.error_flags, now, kShortWindow);
        pruneTimedFloats(state.handshake_flags, now, kShortWindow);
        pruneTimes(state.reconnects, now, kLongWindow);
        pruneTimes(state.breadth_events, now, kLongWindow);
        pruneTimedFloats(state.message_sizes, now, kLongWindow);
        pruneTimedStrings(state.coap_types, now, kShortWindow);
        pruneTimedFloats(state.option_counts, now, kShortWindow);

        msg_count_window = static_cast<float>(state.message_times.size());
        unique_resource_count = uniqueRecentResources(state.resources);
        session_seconds = std::chrono::duration_cast<std::chrono::duration<float>>(now - state.session_start).count();
        error_rate = averageTimedFloat(state.error_flags);
        handshake_complexity = averageTimedFloat(state.handshake_flags);
        subscription_breadth = norm(static_cast<float>(state.breadth_events.size()), 16.0F);
        reconnection_rate = norm(static_cast<float>(state.reconnects.size()), 30.0F);
        message_size_variance = norm(std::sqrt(std::max(varianceTimedFloat(state.message_sizes), 0.0F)), 2048.0F);

        if (!is_mqtt && !state.coap_types.empty()) {
            float con_count = 0.0F;
            float non_count = 0.0F;
            float ack_count = 0.0F;
            float rst_count = 0.0F;
            for (const auto& entry : state.coap_types) {
                if (entry.value == "con") {
                    con_count += 1.0F;
                } else if (entry.value == "non") {
                    non_count += 1.0F;
                } else if (entry.value == "ack") {
                    ack_count += 1.0F;
                } else if (entry.value == "rst") {
                    rst_count += 1.0F;
                }
            }
            const float total = static_cast<float>(state.coap_types.size());
            con_ratio = con_count / total;
            non_ratio = non_count / total;
            ack_ratio = ack_count / total;
            rst_ratio = rst_count / total;
        }
        mean_option_count = averageTimedFloat(state.option_counts);
    }

    NormalizedFeatureVector out{};
    out.fill(0.0F);

    const float msg_rate_derived = norm(msg_count_window, 20.0F);
    const float normalized_inter_arrival = 1.0F - clamp01(inter_arrival_ms / kInterArrivalCapMs);
    const float payload_size = norm(std::log1p(std::max(byte_count, 0.0F)), std::log1p(4096.0F));
    const float payload_entropy = clamp01(payload_entropy_bits / 8.0F);
    const float resource_depth = normalizedResourceDepth(resource);
    const float resource_entropy = clamp01(stringEntropy(resource) / kPathEntropyCap);
    const float qos_level = is_mqtt ? clamp01(static_cast<float>(contains(raw.detail, "qos:2") ? 1.0F : (contains(raw.detail, "qos:1") ? 0.5F : 0.0F)))
                                    : (is_con ? 1.0F : 0.0F);
    const float session_duration = norm(session_seconds, 300.0F);
    const float unique_resource = norm(static_cast<float>(unique_resource_count), 32.0F);
    const float payload_to_resource_ratio = norm(std::log1p(byte_count / std::max(1.0F, static_cast<float>(resource.size()))), std::log1p(kPayloadToResourceCap));
    const float compliance = 1.0F - error_rate;

    const std::array<float, kNormalizedFeatureDims> normalized = {
        msg_rate_derived,
        normalized_inter_arrival,
        payload_size,
        payload_entropy,
        resource_depth,
        resource_entropy,
        qos_level,
        session_duration,
        unique_resource,
        error_rate,
        handshake_complexity,
        subscription_breadth,
        reconnection_rate,
        payload_to_resource_ratio,
        compliance,
    };

    for (std::size_t i = 0; i < normalized.size(); ++i) {
        out[i] = normalized[i];
    }

    out[15] = is_mqtt ? 1.0F : 0.0F;
    out[16] = is_mqtt ? 0.0F : 1.0F;

    if (is_mqtt) {
        out[17] = contains(raw.detail, "retain") ? 1.0F : 0.0F;
        out[18] = clamp01(static_cast<float>(std::count(raw.detail.begin(), raw.detail.end(), '#') + std::count(raw.detail.begin(), raw.detail.end(), '+')) / 4.0F);
        out[19] = reconnect_event ? 1.0F : 0.2F;
        out[20] = norm([&]() {
            const std::string keepalive = extractTaggedValue(raw.detail, "keepalive:");
            if (keepalive.empty()) {
                return 60.0F;
            }
            try {
                return std::stof(keepalive);
            } catch (...) {
                return 60.0F;
            }
        }(), 300.0F);
        out[21] = contains(raw.detail, "will") ? 1.0F : 0.0F;
        out[22] = contains(raw.detail, "pubrel") || contains(raw.detail, "pubrec") || contains(raw.detail, "pubcomp") ? 1.0F : 0.0F;
        out[23] = sourceIdEntropy(raw.source_id);
        out[24] = message_size_variance;
    } else {
        out[25] = con_ratio;
        out[26] = non_ratio;
        out[27] = ack_ratio;
        out[28] = rst_ratio;
        out[29] = contains(raw.detail, "observe") ? 1.0F : 0.0F;
        out[30] = contains(raw.detail, "blockwise") ? 1.0F : 0.0F;
        out[31] = contains(raw.detail, "token:") ? 0.5F : 0.0F;
        out[32] = norm(mean_option_count, 16.0F);
    }

    return out;
}

}  // namespace

RawFeatureVector extractRawFeatures(const ProtocolEvent& event) {
    RawFeatureVector raw{};
    raw.values = {
        static_cast<float>(event.payload.size()),
        static_cast<float>(event.source_id.size()),
        shannonEntropy(event.payload),
    };
    raw.source_id = event.source_id;
    raw.direction = event.direction;
    raw.event_type = event.event_type;
    raw.detail = event.detail;
    return raw;
}

FeatureComputation computeFeatureVectors(const RawFeatureVector& raw, ProtocolKind protocol) {
    FeatureComputation out{};
    out.behavioral_enabled = envEnabled(kBehavioralWindowsEnv);
    out.legacy = legacyNormalize(raw, protocol);
    out.behavioral = statefulNormalize(raw, protocol);
    out.active = out.behavioral_enabled ? out.behavioral : out.legacy;
    return out;
}

NormalizedFeatureVector normalizeFeatures(const RawFeatureVector& raw, ProtocolKind protocol) {
    return computeFeatureVectors(raw, protocol).active;
}

}  // namespace sentrix::featuremap
