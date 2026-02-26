#include "sentrix/event_log.hpp"

#include <chrono>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <mutex>
#include <sstream>

namespace sentrix::eventlog {

namespace {

std::mutex g_event_log_mutex;

std::string nowIsoUtc() {
    const auto now = std::chrono::system_clock::now();
    const std::time_t now_time = std::chrono::system_clock::to_time_t(now);

    std::tm utc_tm{};
#if defined(_WIN32)
    gmtime_s(&utc_tm, &now_time);
#else
    gmtime_r(&now_time, &utc_tm);
#endif

    std::ostringstream oss;
    oss << std::put_time(&utc_tm, "%Y-%m-%dT%H:%M:%SZ");
    return oss.str();
}

std::string escapeJson(const std::string& input) {
    std::string output;
    output.reserve(input.size());

    for (const char c : input) {
        if (c == '\\') {
            output += "\\\\";
        } else if (c == '"') {
            output += "\\\"";
        } else if (c == '\n') {
            output += "\\n";
        } else {
            output += c;
        }
    }

    return output;
}

}  // namespace

void appendEvent(
    const std::string& output_path,
    const std::string& protocol,
    const std::string& direction,
    const std::string& event_type,
    std::size_t bytes,
    const std::string& detail) {
    if (output_path.empty()) {
        return;
    }

    std::lock_guard<std::mutex> lock(g_event_log_mutex);

    std::ofstream out(output_path, std::ios::app);
    if (!out.is_open()) {
        return;
    }

    out << '{'
        << "\"ts\":\"" << nowIsoUtc() << "\"," 
        << "\"protocol\":\"" << escapeJson(protocol) << "\"," 
        << "\"direction\":\"" << escapeJson(direction) << "\"," 
        << "\"event\":\"" << escapeJson(event_type) << "\"," 
        << "\"bytes\":" << bytes << ','
        << "\"detail\":\"" << escapeJson(detail) << "\""
        << "}" << '\n';
}

}  // namespace sentrix::eventlog
