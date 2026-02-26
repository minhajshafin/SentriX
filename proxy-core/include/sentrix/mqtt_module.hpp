#pragma once

#include <atomic>
#include <mutex>
#include <thread>
#include <vector>

#include "sentrix/protocol_module.hpp"

namespace sentrix {

class MqttModule final : public IProtocolModule {
public:
    MqttModule();
    ~MqttModule() override;

    const char* name() const override;
    void start() override;
    void stop() override;

    ProtocolEvent parse(const std::uint8_t* data, std::size_t len) override;
    RawFeatureVector extractFeatures(const ProtocolEvent& event) override;
    NormalizedFeatureVector normalize(const RawFeatureVector& raw) override;
    void mitigate(const MitigationDecision& decision) override;

private:
    void acceptLoop();
    void handleClient(int client_fd);
    int connectToBroker() const;
    void closeTrackedSockets();
    static std::size_t estimateMqttFrames(const std::uint8_t* data, std::size_t len);

    std::atomic<bool> running_{false};
    std::thread accept_thread_;
    std::vector<std::thread> client_threads_;
    std::mutex clients_mutex_;

    int listen_fd_ = -1;
    std::mutex sockets_mutex_;
    std::vector<int> tracked_sockets_;

    int listen_port_ = 1884;
    std::string broker_host_ = "mosquitto";
    int broker_port_ = 1883;
};

}  // namespace sentrix
