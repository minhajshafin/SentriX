#include <algorithm>
#include <array>
#include <cerrno>
#include <cstring>
#include <cstdlib>
#include <iostream>
#include <sstream>

#include <arpa/inet.h>
#include <netdb.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#include "sentrix/mqtt_module.hpp"
#include "sentrix/detection_pipeline.hpp"
#include "sentrix/event_log.hpp"
#include "sentrix/feature_mapping.hpp"
#include "sentrix/metrics_store.hpp"

namespace sentrix {

namespace {

constexpr std::size_t kBufferSize = 4096;

int envToInt(const char* value, int fallback) {
    if (value == nullptr) {
        return fallback;
    }

    char* end = nullptr;
    const long parsed = std::strtol(value, &end, 10);
    if (end == value || *end != '\0' || parsed <= 0 || parsed > 65535) {
        return fallback;
    }

    return static_cast<int>(parsed);
}

bool decodeRemainingLength(
    const std::uint8_t* data,
    std::size_t len,
    std::size_t& remaining_length,
    std::size_t& bytes_used) {
    if (len < 2) {
        return false;
    }

    std::size_t multiplier = 1;
    remaining_length = 0;
    bytes_used = 0;

    while (1 + bytes_used < len) {
        const std::uint8_t encoded = data[1 + bytes_used];
        remaining_length += static_cast<std::size_t>(encoded & 0x7F) * multiplier;
        ++bytes_used;

        if ((encoded & 0x80) == 0) {
            return true;
        }

        multiplier *= 128;
        if (bytes_used >= 4) {
            return false;
        }
    }

    return false;
}

bool readMqttUtf8(const std::uint8_t* data, std::size_t len, std::size_t& offset, std::string& out) {
    if (offset + 2 > len) {
        return false;
    }

    const std::size_t str_len =
        (static_cast<std::size_t>(data[offset]) << 8) | static_cast<std::size_t>(data[offset + 1]);
    offset += 2;
    if (offset + str_len > len) {
        return false;
    }

    out.assign(reinterpret_cast<const char*>(data + offset), str_len);
    offset += str_len;
    return true;
}

bool mqttParseConnectMeta(
    const std::uint8_t* data,
    std::size_t len,
    std::string& client_id,
    bool& will_flag,
    std::uint16_t& keepalive_seconds) {
    std::size_t remaining_length = 0;
    std::size_t bytes_used = 0;
    if (!decodeRemainingLength(data, len, remaining_length, bytes_used)) {
        return false;
    }

    std::size_t offset = 1 + bytes_used;
    std::string protocol_name;
    if (!readMqttUtf8(data, len, offset, protocol_name)) {
        return false;
    }

    if (offset + 4 > len) {
        return false;
    }

    const std::uint8_t connect_flags = data[offset + 1];
    keepalive_seconds = static_cast<std::uint16_t>((static_cast<std::uint16_t>(data[offset + 2]) << 8) | data[offset + 3]);
    will_flag = (connect_flags & 0x04U) != 0;
    offset += 4;

    return readMqttUtf8(data, len, offset, client_id);
}

std::string mqttPacketName(std::uint8_t packet_type) {
    switch (packet_type) {
        case 1:
            return "connect";
        case 2:
            return "connack";
        case 3:
            return "publish";
        case 4:
            return "puback";
        case 5:
            return "pubrec";
        case 6:
            return "pubrel";
        case 7:
            return "pubcomp";
        case 8:
            return "subscribe";
        case 9:
            return "suback";
        case 10:
            return "unsubscribe";
        case 11:
            return "unsuback";
        case 12:
            return "pingreq";
        case 13:
            return "pingresp";
        case 14:
            return "disconnect";
        default:
            return "unknown";
    }
}

std::string mqttPublishTopic(const std::uint8_t* data, std::size_t len) {
    std::size_t remaining_length = 0;
    std::size_t bytes_used = 0;
    if (!decodeRemainingLength(data, len, remaining_length, bytes_used)) {
        return {};
    }

    std::size_t offset = 1 + bytes_used;
    std::string topic;
    if (!readMqttUtf8(data, len, offset, topic)) {
        return {};
    }
    return topic;
}

bool mqttSubscribeHasWildcard(const std::uint8_t* data, std::size_t len) {
    std::size_t remaining_length = 0;
    std::size_t bytes_used = 0;
    if (!decodeRemainingLength(data, len, remaining_length, bytes_used)) {
        return false;
    }

    std::size_t offset = 1 + bytes_used;
    if (offset + 2 > len) {
        return false;
    }

    offset += 2;  // packet identifier
    while (offset < len) {
        std::string topic_filter;
        if (!readMqttUtf8(data, len, offset, topic_filter)) {
            return false;
        }
        if (topic_filter.find('#') != std::string::npos || topic_filter.find('+') != std::string::npos) {
            return true;
        }
        if (offset >= len) {
            break;
        }
        ++offset;  // requested qos
    }

    return false;
}

}  // namespace

MqttModule::MqttModule() {
    listen_port_ = envToInt(std::getenv("SENTRIX_MQTT_PROXY_PORT"), 1884);
    broker_port_ = envToInt(std::getenv("SENTRIX_MQTT_BROKER_PORT"), 1883);

    if (const char* host = std::getenv("SENTRIX_MQTT_BROKER_HOST"); host != nullptr && *host != '\0') {
        broker_host_ = host;
    }

    if (const char* event_path = std::getenv("SENTRIX_EVENTS_PATH"); event_path != nullptr && *event_path != '\0') {
        events_path_ = event_path;
    } else {
        events_path_ = "/tmp/sentrix_events.log";
    }
}

MqttModule::~MqttModule() {
    stop();
}

const char* MqttModule::name() const {
    return "mqtt";
}

void MqttModule::start() {
    if (running_.exchange(true)) {
        return;
    }

    listen_fd_ = ::socket(AF_INET, SOCK_STREAM, 0);
    if (listen_fd_ < 0) {
        std::cerr << "[MQTT] failed to create listen socket: " << std::strerror(errno) << std::endl;
        running_.store(false);
        return;
    }

    {
        std::lock_guard<std::mutex> lock(sockets_mutex_);
        tracked_sockets_.push_back(listen_fd_);
    }

    constexpr int reuse = 1;
    if (::setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse)) < 0) {
        std::cerr << "[MQTT] setsockopt(SO_REUSEADDR) failed: " << std::strerror(errno) << std::endl;
    }

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(static_cast<std::uint16_t>(listen_port_));

    if (::bind(listen_fd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
        std::cerr << "[MQTT] bind failed on port " << listen_port_ << ": " << std::strerror(errno) << std::endl;
        stop();
        return;
    }

    if (::listen(listen_fd_, 128) < 0) {
        std::cerr << "[MQTT] listen failed: " << std::strerror(errno) << std::endl;
        stop();
        return;
    }

    std::cout << "[MQTT] proxy listening on 0.0.0.0:" << listen_port_
              << " -> " << broker_host_ << ':' << broker_port_ << std::endl;
    eventlog::appendEvent(events_path_, "mqtt", "internal", "module_start", 0, "proxy online");

    accept_thread_ = std::thread(&MqttModule::acceptLoop, this);
}

void MqttModule::stop() {
    if (!running_.exchange(false)) {
        return;
    }

    closeTrackedSockets();

    if (accept_thread_.joinable()) {
        accept_thread_.join();
    }

    {
        std::lock_guard<std::mutex> lock(clients_mutex_);
        for (auto& thread : client_threads_) {
            if (thread.joinable()) {
                thread.join();
            }
        }
        client_threads_.clear();
    }

    std::cout << "[MQTT] module stopped" << std::endl;
    eventlog::appendEvent(events_path_, "mqtt", "internal", "module_stop", 0, "proxy stopped");
}

ProtocolEvent MqttModule::parse(const std::uint8_t* data, std::size_t len) {
    ProtocolEvent event{};
    event.protocol = ProtocolKind::Mqtt;
    event.source_id = "mqtt-client";
    event.direction = "incoming";
    event.event_type = "traffic";
    event.payload.assign(data, data + len);

    if (len == 0) {
        event.detail = "client_to_broker|malform|empty";
        return event;
    }

    const std::uint8_t packet_type = static_cast<std::uint8_t>((data[0] >> 4) & 0x0F);
    std::ostringstream detail;
    detail << "client_to_broker|" << mqttPacketName(packet_type);

    std::size_t remaining_length = 0;
    std::size_t bytes_used = 0;
    const bool valid_remaining = decodeRemainingLength(data, len, remaining_length, bytes_used);
    if (!valid_remaining || (1 + bytes_used + remaining_length) > len) {
        detail << "|malform";
    }

    if (packet_type == 1) {
        event.event_type = "connection_open";
        std::string client_id;
        bool will_flag = false;
        std::uint16_t keepalive_seconds = 0;
        if (mqttParseConnectMeta(data, len, client_id, will_flag, keepalive_seconds) && !client_id.empty()) {
            event.source_id = client_id;
            detail << "|client_id:" << client_id;
        }
        if (will_flag) {
            detail << "|will";
        }
        detail << "|keepalive:" << keepalive_seconds;
    } else if (packet_type == 3) {
        const std::uint8_t qos = static_cast<std::uint8_t>((data[0] >> 1) & 0x03);
        const bool retain = (data[0] & 0x01U) != 0;
        const std::string topic = mqttPublishTopic(data, len);
        detail << "|qos:" << static_cast<unsigned int>(qos);
        if (retain) {
            detail << "|retain";
        }
        if (!topic.empty()) {
            detail << "|topic:" << topic;
        }
    } else if (packet_type == 8 && mqttSubscribeHasWildcard(data, len)) {
        detail << "|wildcard";
    }

    event.detail = detail.str();
    return event;
}

RawFeatureVector MqttModule::extractFeatures(const ProtocolEvent& event) {
    return featuremap::extractRawFeatures(event);
}

NormalizedFeatureVector MqttModule::normalize(const RawFeatureVector& raw) {
    return featuremap::normalizeFeatures(raw, ProtocolKind::Mqtt);
}

void MqttModule::mitigate(const MitigationDecision& decision) {
    std::cout << "[MQTT] mitigation action=" << decision.action
              << " allow=" << (decision.allow ? "true" : "false") << std::endl;
}

void MqttModule::acceptLoop() {
    while (running_.load()) {
        sockaddr_in client_addr{};
        socklen_t client_len = sizeof(client_addr);
        const int client_fd = ::accept(listen_fd_, reinterpret_cast<sockaddr*>(&client_addr), &client_len);
        if (client_fd < 0) {
            if (!running_.load()) {
                break;
            }
            if (errno == EINTR) {
                continue;
            }
            std::cerr << "[MQTT] accept failed: " << std::strerror(errno) << std::endl;
            continue;
        }

        {
            std::lock_guard<std::mutex> lock(sockets_mutex_);
            tracked_sockets_.push_back(client_fd);
        }

        eventlog::appendEvent(events_path_, "mqtt", "incoming", "connection_open", 0, "client accepted");

        std::lock_guard<std::mutex> lock(clients_mutex_);
        client_threads_.emplace_back(&MqttModule::handleClient, this, client_fd);
    }
}

void MqttModule::handleClient(int client_fd) {
    const int broker_fd = connectToBroker();
    if (broker_fd < 0) {
        ::close(client_fd);
        return;
    }

    {
        std::lock_guard<std::mutex> lock(sockets_mutex_);
        tracked_sockets_.push_back(broker_fd);
    }

    std::array<std::uint8_t, kBufferSize> buffer{};

    while (running_.load()) {
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(client_fd, &read_fds);
        FD_SET(broker_fd, &read_fds);

        const int max_fd = std::max(client_fd, broker_fd);
        const int ready = ::select(max_fd + 1, &read_fds, nullptr, nullptr, nullptr);
        if (ready < 0) {
            if (errno == EINTR) {
                continue;
            }
            std::cerr << "[MQTT] select failed: " << std::strerror(errno) << std::endl;
            break;
        }

        if (FD_ISSET(client_fd, &read_fds)) {
            const ssize_t received = ::recv(client_fd, buffer.data(), buffer.size(), 0);
            if (received <= 0) {
                break;
            }

            ProtocolEvent event = parse(buffer.data(), static_cast<std::size_t>(received));
            event.direction = "incoming";
            if (event.detail.rfind("client_to_broker|", 0) != 0) {
                event.detail = "client_to_broker|" + event.detail;
            }
            const RawFeatureVector raw = extractFeatures(event);
            const NormalizedFeatureVector normalized = normalize(raw);
            const detection::DetectionResult detection_result =
                detection::evaluate(normalized, ProtocolKind::Mqtt);
            mitigate(detection_result.decision);

            if (!detection_result.decision.allow) {
                metrics::addDetections(1);
                eventlog::appendEvent(
                    events_path_,
                    "mqtt",
                    "mitigation",
                    detection_result.decision.action,
                    static_cast<std::size_t>(received),
                    detection_result.decision.reason);
                continue;
            }

            const std::size_t frame_count = estimateMqttFrames(buffer.data(), static_cast<std::size_t>(received));
            if (frame_count > 0) {
                metrics::addMqttMessages(frame_count);
            }
            eventlog::appendEvent(
                events_path_,
                "mqtt",
                "incoming",
                event.event_type,
                static_cast<std::size_t>(received),
                event.detail);

            ssize_t sent_total = 0;
            while (sent_total < received) {
                const ssize_t sent = ::send(
                    broker_fd,
                    buffer.data() + sent_total,
                    static_cast<std::size_t>(received - sent_total),
                    0);
                if (sent <= 0) {
                    sent_total = -1;
                    break;
                }
                sent_total += sent;
            }

            if (sent_total < 0) {
                break;
            }
        }

        if (FD_ISSET(broker_fd, &read_fds)) {
            const ssize_t received = ::recv(broker_fd, buffer.data(), buffer.size(), 0);
            if (received <= 0) {
                break;
            }

            ProtocolEvent event = parse(buffer.data(), static_cast<std::size_t>(received));
            event.direction = "outgoing";
            if (event.detail.rfind("client_to_broker|", 0) == 0) {
                event.detail.replace(0, std::strlen("client_to_broker"), "broker_to_client");
            } else {
                event.detail = "broker_to_client|" + event.detail;
            }

            eventlog::appendEvent(
                events_path_,
                "mqtt",
                "outgoing",
                event.event_type,
                static_cast<std::size_t>(received),
                event.detail);

            ssize_t sent_total = 0;
            while (sent_total < received) {
                const ssize_t sent = ::send(
                    client_fd,
                    buffer.data() + sent_total,
                    static_cast<std::size_t>(received - sent_total),
                    0);
                if (sent <= 0) {
                    sent_total = -1;
                    break;
                }
                sent_total += sent;
            }

            if (sent_total < 0) {
                break;
            }
        }
    }

    ::close(client_fd);
    ::close(broker_fd);
    eventlog::appendEvent(events_path_, "mqtt", "internal", "connection_close", 0, "client disconnected");
}

int MqttModule::connectToBroker() const {
    addrinfo hints{};
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;

    addrinfo* result = nullptr;
    const std::string port = std::to_string(broker_port_);
    if (::getaddrinfo(broker_host_.c_str(), port.c_str(), &hints, &result) != 0) {
        std::cerr << "[MQTT] getaddrinfo failed for broker host " << broker_host_ << std::endl;
        return -1;
    }

    int broker_fd = -1;
    for (addrinfo* current = result; current != nullptr; current = current->ai_next) {
        broker_fd = ::socket(current->ai_family, current->ai_socktype, current->ai_protocol);
        if (broker_fd < 0) {
            continue;
        }

        if (::connect(broker_fd, current->ai_addr, current->ai_addrlen) == 0) {
            break;
        }

        ::close(broker_fd);
        broker_fd = -1;
    }

    ::freeaddrinfo(result);

    if (broker_fd < 0) {
        std::cerr << "[MQTT] connect to broker failed " << broker_host_ << ':' << broker_port_ << std::endl;
    }

    return broker_fd;
}

void MqttModule::closeTrackedSockets() {
    std::lock_guard<std::mutex> lock(sockets_mutex_);
    for (const int fd : tracked_sockets_) {
        if (fd >= 0) {
            ::shutdown(fd, SHUT_RDWR);
            ::close(fd);
        }
    }
    tracked_sockets_.clear();
    listen_fd_ = -1;
}

std::size_t MqttModule::estimateMqttFrames(const std::uint8_t* data, std::size_t len) {
    std::size_t offset = 0;
    std::size_t frames = 0;

    while (offset + 2 <= len) {
        std::size_t multiplier = 1;
        std::size_t remaining_length = 0;
        std::size_t bytes_used = 0;

        while (offset + 1 + bytes_used < len) {
            const std::uint8_t encoded = data[offset + 1 + bytes_used];
            remaining_length += static_cast<std::size_t>(encoded & 0x7F) * multiplier;
            multiplier *= 128;
            ++bytes_used;

            if ((encoded & 0x80) == 0) {
                break;
            }

            if (bytes_used >= 4) {
                return frames;
            }
        }

        if (offset + 1 + bytes_used > len) {
            break;
        }

        const std::size_t packet_size = 1 + bytes_used + remaining_length;
        if (offset + packet_size > len) {
            break;
        }

        ++frames;
        offset += packet_size;
    }

    return frames;
}

}  // namespace sentrix
