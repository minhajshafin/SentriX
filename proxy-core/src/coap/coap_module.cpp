#include <algorithm>
#include <array>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <iostream>

#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <unistd.h>

#include "sentrix/coap_module.hpp"
#include "sentrix/detection_pipeline.hpp"
#include "sentrix/event_log.hpp"
#include "sentrix/metrics_store.hpp"

namespace sentrix {

namespace {

constexpr std::size_t kBufferSize = 2048;

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

}  // namespace

CoapModule::CoapModule() {
    listen_port_ = envToInt(std::getenv("SENTRIX_COAP_PROXY_PORT"), 5684);
    backend_port_ = envToInt(std::getenv("SENTRIX_COAP_BACKEND_PORT"), 5683);

    if (const char* host = std::getenv("SENTRIX_COAP_BACKEND_HOST"); host != nullptr && *host != '\0') {
        backend_host_ = host;
    }

    if (const char* path = std::getenv("SENTRIX_EVENTS_PATH"); path != nullptr && *path != '\0') {
        events_path_ = path;
    } else {
        events_path_ = "/tmp/sentrix_events.log";
    }
}

CoapModule::~CoapModule() {
    stop();
}

const char* CoapModule::name() const {
    return "coap";
}

void CoapModule::start() {
    if (running_.exchange(true)) {
        return;
    }

    if (!createSockets()) {
        running_.store(false);
        return;
    }

    io_thread_ = std::thread(&CoapModule::ioLoop, this);

    std::cout << "[CoAP] proxy listening on 0.0.0.0:" << listen_port_
              << " -> " << backend_host_ << ':' << backend_port_ << std::endl;
    eventlog::appendEvent(events_path_, "coap", "internal", "module_start", 0, "proxy online");
}

void CoapModule::stop() {
    if (!running_.exchange(false)) {
        return;
    }

    closeSockets();

    if (io_thread_.joinable()) {
        io_thread_.join();
    }

    {
        std::lock_guard<std::mutex> lock(map_mutex_);
        mid_to_client_.clear();
    }

    std::cout << "[CoAP] module stopped" << std::endl;
    eventlog::appendEvent(events_path_, "coap", "internal", "module_stop", 0, "proxy stopped");
}

ProtocolEvent CoapModule::parse(const std::uint8_t* data, std::size_t len) {
    ProtocolEvent event{};
    event.protocol = ProtocolKind::Coap;
    event.source_id = "coap-source";
    event.payload.assign(data, data + len);
    return event;
}

RawFeatureVector CoapModule::extractFeatures(const ProtocolEvent& event) {
    RawFeatureVector features{};
    features.values = {
        static_cast<float>(event.payload.size()),
        static_cast<float>(event.source_id.size()),
    };
    return features;
}

NormalizedFeatureVector CoapModule::normalize(const RawFeatureVector& raw) {
    NormalizedFeatureVector normalized{};
    normalized.fill(0.0F);

    if (!raw.values.empty()) {
        normalized[2] = std::min(raw.values[0] / 1024.0F, 1.0F);
    }

    normalized[15] = 0.0F;
    normalized[16] = 1.0F;
    return normalized;
}

void CoapModule::mitigate(const MitigationDecision& decision) {
    std::cout << "[CoAP] mitigation action=" << decision.action
              << " allow=" << (decision.allow ? "true" : "false") << std::endl;
}

void CoapModule::ioLoop() {
    std::array<std::uint8_t, kBufferSize> buffer{};

    while (running_.load()) {
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(listen_fd_, &read_fds);
        FD_SET(backend_fd_, &read_fds);

        const int max_fd = std::max(listen_fd_, backend_fd_);
        const int ready = ::select(max_fd + 1, &read_fds, nullptr, nullptr, nullptr);
        if (ready < 0) {
            if (errno == EINTR) {
                continue;
            }
            if (!running_.load()) {
                break;
            }
            std::cerr << "[CoAP] select failed: " << std::strerror(errno) << std::endl;
            continue;
        }

        if (FD_ISSET(listen_fd_, &read_fds)) {
            sockaddr_in client_addr{};
            socklen_t client_len = sizeof(client_addr);
            const ssize_t received = ::recvfrom(
                listen_fd_,
                buffer.data(),
                buffer.size(),
                0,
                reinterpret_cast<sockaddr*>(&client_addr),
                &client_len);

            if (received > 0) {
                const ProtocolEvent event = parse(buffer.data(), static_cast<std::size_t>(received));
                const RawFeatureVector raw = extractFeatures(event);
                const NormalizedFeatureVector normalized = normalize(raw);
                const detection::DetectionResult detection_result =
                    detection::evaluate(normalized, ProtocolKind::Coap);
                mitigate(detection_result.decision);

                if (!detection_result.decision.allow) {
                    metrics::addDetections(1);
                    eventlog::appendEvent(
                        events_path_,
                        "coap",
                        "mitigation",
                        detection_result.decision.action,
                        static_cast<std::size_t>(received),
                        detection_result.decision.reason);
                    continue;
                }

                metrics::addCoapMessages(1);

                std::uint16_t message_id = 0;
                if (readMessageId(buffer.data(), static_cast<std::size_t>(received), message_id)) {
                    std::lock_guard<std::mutex> lock(map_mutex_);
                    mid_to_client_[message_id] = {
                        endpointToString(client_addr),
                        ntohs(client_addr.sin_port),
                    };
                }

                const ssize_t sent = ::send(backend_fd_, buffer.data(), static_cast<std::size_t>(received), 0);
                if (sent < 0) {
                    std::cerr << "[CoAP] send to backend failed: " << std::strerror(errno) << std::endl;
                } else {
                    eventlog::appendEvent(
                        events_path_,
                        "coap",
                        "incoming",
                        "traffic",
                        static_cast<std::size_t>(received),
                        "client_to_backend");
                }
            }
        }

        if (FD_ISSET(backend_fd_, &read_fds)) {
            const ssize_t received = ::recv(backend_fd_, buffer.data(), buffer.size(), 0);
            if (received > 0) {
                std::uint16_t message_id = 0;
                bool routed = false;

                if (readMessageId(buffer.data(), static_cast<std::size_t>(received), message_id)) {
                    ClientEndpoint endpoint{};
                    {
                        std::lock_guard<std::mutex> lock(map_mutex_);
                        auto it = mid_to_client_.find(message_id);
                        if (it != mid_to_client_.end()) {
                            endpoint = it->second;
                            mid_to_client_.erase(it);
                        }
                    }

                    if (!endpoint.ip.empty()) {
                        sockaddr_in client_addr{};
                        client_addr.sin_family = AF_INET;
                        client_addr.sin_port = htons(endpoint.port);
                        if (::inet_pton(AF_INET, endpoint.ip.c_str(), &client_addr.sin_addr) == 1) {
                            const ssize_t sent = ::sendto(
                                listen_fd_,
                                buffer.data(),
                                static_cast<std::size_t>(received),
                                0,
                                reinterpret_cast<sockaddr*>(&client_addr),
                                sizeof(client_addr));
                            if (sent >= 0) {
                                routed = true;
                            }
                        }
                    }
                }

                if (routed) {
                    eventlog::appendEvent(
                        events_path_,
                        "coap",
                        "outgoing",
                        "traffic",
                        static_cast<std::size_t>(received),
                        "backend_to_client");
                } else {
                    eventlog::appendEvent(
                        events_path_,
                        "coap",
                        "internal",
                        "unrouted_response",
                        static_cast<std::size_t>(received),
                        "missing message-id mapping");
                }
            }
        }
    }
}

bool CoapModule::createSockets() {
    listen_fd_ = ::socket(AF_INET, SOCK_DGRAM, 0);
    if (listen_fd_ < 0) {
        std::cerr << "[CoAP] failed to create listen socket: " << std::strerror(errno) << std::endl;
        return false;
    }

    constexpr int reuse = 1;
    if (::setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse)) < 0) {
        std::cerr << "[CoAP] setsockopt(SO_REUSEADDR) failed: " << std::strerror(errno) << std::endl;
    }

    sockaddr_in listen_addr{};
    listen_addr.sin_family = AF_INET;
    listen_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    listen_addr.sin_port = htons(static_cast<std::uint16_t>(listen_port_));

    if (::bind(listen_fd_, reinterpret_cast<sockaddr*>(&listen_addr), sizeof(listen_addr)) < 0) {
        std::cerr << "[CoAP] bind failed on port " << listen_port_ << ": " << std::strerror(errno) << std::endl;
        closeSockets();
        return false;
    }

    sockaddr_in backend_addr{};
    backend_fd_ = connectToBackend(backend_addr);
    if (backend_fd_ < 0) {
        closeSockets();
        return false;
    }

    return true;
}

void CoapModule::closeSockets() {
    if (listen_fd_ >= 0) {
        ::close(listen_fd_);
        listen_fd_ = -1;
    }

    if (backend_fd_ >= 0) {
        ::close(backend_fd_);
        backend_fd_ = -1;
    }
}

int CoapModule::connectToBackend(sockaddr_in& backend_addr) const {
    addrinfo hints{};
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_DGRAM;

    addrinfo* result = nullptr;
    const std::string port = std::to_string(backend_port_);
    if (::getaddrinfo(backend_host_.c_str(), port.c_str(), &hints, &result) != 0) {
        std::cerr << "[CoAP] getaddrinfo failed for backend host " << backend_host_ << std::endl;
        return -1;
    }

    int fd = -1;
    for (addrinfo* current = result; current != nullptr; current = current->ai_next) {
        fd = ::socket(current->ai_family, current->ai_socktype, current->ai_protocol);
        if (fd < 0) {
            continue;
        }

        if (::connect(fd, current->ai_addr, current->ai_addrlen) == 0) {
            std::memcpy(&backend_addr, current->ai_addr, sizeof(sockaddr_in));
            break;
        }

        ::close(fd);
        fd = -1;
    }

    ::freeaddrinfo(result);

    if (fd < 0) {
        std::cerr << "[CoAP] connect to backend failed " << backend_host_ << ':' << backend_port_ << std::endl;
    }

    return fd;
}

bool CoapModule::readMessageId(const std::uint8_t* data, std::size_t len, std::uint16_t& message_id) {
    if (len < 4) {
        return false;
    }

    message_id = static_cast<std::uint16_t>((static_cast<std::uint16_t>(data[2]) << 8) | data[3]);
    return true;
}

std::string CoapModule::endpointToString(const sockaddr_in& addr) {
    char ip[INET_ADDRSTRLEN] = {0};
    if (::inet_ntop(AF_INET, &addr.sin_addr, ip, sizeof(ip)) == nullptr) {
        return {};
    }
    return ip;
}

}  // namespace sentrix
