#include "sentrix/proxy_core.hpp"

namespace sentrix {

void ProxyCore::registerModule(std::unique_ptr<IProtocolModule> module) {
    modules_.push_back(std::move(module));
}

void ProxyCore::startAll() {
    for (auto& module : modules_) {
        module->start();
    }
}

void ProxyCore::stopAll() {
    for (auto& module : modules_) {
        module->stop();
    }
}

}  // namespace sentrix
