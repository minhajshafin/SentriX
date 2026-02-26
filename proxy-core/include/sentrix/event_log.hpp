#pragma once

#include <cstddef>
#include <string>

namespace sentrix::eventlog {

void appendEvent(
    const std::string& output_path,
    const std::string& protocol,
    const std::string& direction,
    const std::string& event_type,
    std::size_t bytes,
    const std::string& detail = "");

}  // namespace sentrix::eventlog
