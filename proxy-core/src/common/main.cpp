#include <iostream>
#include <memory>
#include <atomic>
#include <csignal>
#include <thread>
#include <chrono>

#include "sentrix/coap_module.hpp"
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

    core.registerModule(std::make_unique<sentrix::MqttModule>());
    core.registerModule(std::make_unique<sentrix::CoapModule>());

    core.startAll();
    std::cout << "SentriX proxy-core scaffold is running (stub mode). Press Ctrl+C to stop." << std::endl;

    std::signal(SIGINT, handleSignal);
    std::signal(SIGTERM, handleSignal);

    while (keep_running.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(250));
    }

    core.stopAll();

    return 0;
}
