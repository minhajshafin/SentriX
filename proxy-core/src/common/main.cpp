#include <iostream>
#include <memory>
#include <atomic>
#include <csignal>
#include <thread>
#include <chrono>
#include <cstdlib>
#include <string>

#include "sentrix/coap_module.hpp"
#include "sentrix/metrics_store.hpp"
#include "sentrix/mqtt_module.hpp"
#include "sentrix/proxy_core.hpp"

namespace {

std::atomic<bool> keep_running{true};

void handleSignal(int) {
    keep_running.store(false);
}

}  // namespace

int main() {
    sentrix::ProxyCore core;
    const std::string metrics_path =
        (std::getenv("SENTRIX_METRICS_PATH") != nullptr)
            ? std::getenv("SENTRIX_METRICS_PATH")
            : "/tmp/sentrix_metrics.json";

    core.registerModule(std::make_unique<sentrix::MqttModule>());
    core.registerModule(std::make_unique<sentrix::CoapModule>());

    core.startAll();
    std::cout << "SentriX proxy-core scaffold is running (stub mode). Press Ctrl+C to stop." << std::endl;

    std::signal(SIGINT, handleSignal);
    std::signal(SIGTERM, handleSignal);

    auto next_flush = std::chrono::steady_clock::now();
    while (keep_running.load()) {
        const auto now = std::chrono::steady_clock::now();
        if (now >= next_flush) {
            sentrix::metrics::writeSnapshot(metrics_path);
            next_flush = now + std::chrono::seconds(1);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(250));
    }

    sentrix::metrics::writeSnapshot(metrics_path);

    core.stopAll();

    return 0;
}
