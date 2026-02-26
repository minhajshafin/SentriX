#pragma once

#include <atomic>
#include <mutex>
#include <netinet/in.h>
#include <string>
#include <thread>
#include <unordered_map>

#include "sentrix/protocol_module.hpp"

namespace sentrix {

class CoapModule final : public IProtocolModule {
public:
    CoapModule();
    ~CoapModule() override;

    const char* name() const override;
    void start() override;
    void stop() override;

    ProtocolEvent parse(const std::uint8_t* data, std::size_t len) override;
    RawFeatureVector extractFeatures(const ProtocolEvent& event) override;
    NormalizedFeatureVector normalize(const RawFeatureVector& raw) override;
    void mitigate(const MitigationDecision& decision) override;

private:
    struct ClientEndpoint {
        std::string ip;
        std::uint16_t port;
    };

    void ioLoop();
    bool createSockets();
    void closeSockets();
    int connectToBackend(sockaddr_in& backend_addr) const;

    static bool readMessageId(const std::uint8_t* data, std::size_t len, std::uint16_t& message_id);
    static std::string endpointToString(const sockaddr_in& addr);

    std::atomic<bool> running_{false};
    std::thread io_thread_;

    int listen_fd_ = -1;
    int backend_fd_ = -1;

    int listen_port_ = 5684;
    std::string backend_host_ = "californium-backend";
    int backend_port_ = 5683;
    std::string events_path_;

    std::mutex map_mutex_;
    std::unordered_map<std::uint16_t, ClientEndpoint> mid_to_client_;
};

}  // namespace sentrix
