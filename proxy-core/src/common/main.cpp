#include <iostream>
#include <memory>

#include "sentrix/coap_module.hpp"
#include "sentrix/mqtt_module.hpp"
#include "sentrix/proxy_core.hpp"

int main() {
    sentrix::ProxyCore core;

    core.registerModule(std::make_unique<sentrix::MqttModule>());
    core.registerModule(std::make_unique<sentrix::CoapModule>());

    core.startAll();
    std::cout << "SentriX proxy-core scaffold is running (stub mode)." << std::endl;
    core.stopAll();

    return 0;
}
