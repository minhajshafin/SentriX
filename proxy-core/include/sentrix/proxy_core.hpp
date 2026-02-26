#pragma once

#include <memory>
#include <vector>

#include "sentrix/protocol_module.hpp"

namespace sentrix {

class ProxyCore {
public:
    void registerModule(std::unique_ptr<IProtocolModule> module);
    void startAll();
    void stopAll();

private:
    std::vector<std::unique_ptr<IProtocolModule>> modules_;
};

}  // namespace sentrix
