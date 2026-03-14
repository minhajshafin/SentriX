#include "sentrix/feature_mapping.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <string>

namespace sentrix::featuremap {

namespace {

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

}  // namespace

RawFeatureVector extractRawFeatures(const ProtocolEvent& event) {
    RawFeatureVector raw{};
    raw.values = {
        static_cast<float>(event.payload.size()),
        static_cast<float>(event.source_id.size()),
    };
    raw.direction = event.direction;
    raw.event_type = event.event_type;
    raw.detail = event.detail;
    return raw;
}

NormalizedFeatureVector normalizeFeatures(const RawFeatureVector& raw, ProtocolKind protocol) {
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
        aux = {0.0F, 0.0F, 0.0F, 0.0F, 0.0F, 0.0F, 0.0F, 0.0F};
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
    } else {
        for (std::size_t i = 0; i < aux.size(); ++i) {
            out[25 + i] = aux[i];
        }
    }

    return out;
}

}  // namespace sentrix::featuremap
