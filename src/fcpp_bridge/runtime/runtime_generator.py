from pathlib import Path
from fcpp_bridge.log import get_logger

_log = get_logger(__name__)


class RuntimeGenerator:
    """Generate C++ runtime support library for compiled programs."""

    @staticmethod
    def ipc_server_header() -> str:
        """Generate ipc_server.hpp — Unix socket listener."""
        return """
#pragma once
#include <string>
#include <functional>
#include <nlohmann/json.hpp>

namespace fcpp_runtime {

using json = nlohmann::json;

class IpcServer {
public:
    using CommandHandler = std::function<json(const json&)>;

    IpcServer(int port);
    ~IpcServer();

    void register_handler(const std::string& cmd_name, CommandHandler handler);
    void run(bool blocking = true);
    void stop();

private:
    int port_;
    bool running_;
    CommandHandler handlers_[32];
};

}  // namespace fcpp_runtime
"""

    @staticmethod
    def state_serializer_header() -> str:
        """Generate state_serializer.hpp — state to JSON conversion."""
        return """
#pragma once
#include <nlohmann/json.hpp>
#include <vector>

namespace fcpp_runtime {

using json = nlohmann::json;

class StateSerializer {
public:
    template <typename T>
    static json serialize(const T& state) {
        // Specializations provided for primitive types
        return json(state);
    }

    template <>
    static json serialize<double>(const double& state) {
        return json::object({{"value", state}});
    }

    template <>
    static json serialize<int>(const int& state) {
        return json::object({{"value", state}});
    }

    // Generic container support
    template <typename T>
    static json serialize_vector(const std::vector<T>& vec) {
        json arr = json::array();
        for (const auto& item : vec) {
            arr.push_back(serialize(item));
        }
        return arr;
    }
};

}  // namespace fcpp_runtime
"""

    @staticmethod
    def node_manager_header() -> str:
        """Generate node_manager.hpp — dynamic node lifecycle."""
        return """
#pragma once
#include <vector>
#include <map>
#include <functional>

namespace fcpp_runtime {

class NodeManager {
public:
    using StateUpdateCallback = std::function<void(int, const void*)>;

    NodeManager(int initial_node_count);
    ~NodeManager();

    void add_nodes(int count);
    void remove_nodes(int count);
    int node_count() const;

    void set_state_callback(StateUpdateCallback cb);
    void on_node_state_update(int node_id, const void* state);

private:
    std::vector<int> node_ids_;
    StateUpdateCallback state_cb_;
    int next_node_id_;
};

}  // namespace fcpp_runtime
"""

    @staticmethod
    def main_template_header() -> str:
        """Generate main_template.hpp — boilerplate for main()."""
        return """
#pragma once
#include <fcpp/fcpp.hpp>
#include "ipc_server.hpp"
#include "state_serializer.hpp"
#include "node_manager.hpp"

namespace fcpp_runtime {

// Template for generated main() function
template <typename AggregateProgram>
class SwarmSimulator {
public:
    SwarmSimulator(int num_nodes, int ipc_port = 0)
        : num_nodes_(num_nodes), ipc_port_(ipc_port), ipc_server_(ipc_port) {
        // Register standard IPC handlers.
        // ping — liveness probe; no FCPP round is executed.
        ipc_server_.register_handler("ping", [](const json& req) {
            json resp;
            resp["status"] = "pong";
            resp["node_id"] = req.value("node_id", -1);
            return resp;
        });
    }

    void run_step() {
        // Execute one round of the aggregate program
        // - Send neighbor queries
        // - Execute aggregate for each node
        // - Collect results
        // - Notify IPC clients
    }

    void run_until(double time) {
        while (current_time_ < time) {
            run_step();
            current_time_ += dt_;
        }
    }

private:
    int num_nodes_;
    int ipc_port_;
    double current_time_ = 0.0;
    double dt_ = 0.1;
    IpcServer ipc_server_;
};

}  // namespace fcpp_runtime
"""

    @staticmethod
    def write_runtime_headers(output_dir: Path) -> None:
        """Write all runtime headers to directory."""
        output_dir.mkdir(parents=True, exist_ok=True)

        (output_dir / "ipc_server.hpp").write_text(RuntimeGenerator.ipc_server_header())
        (output_dir / "state_serializer.hpp").write_text(
            RuntimeGenerator.state_serializer_header()
        )
        (output_dir / "node_manager.hpp").write_text(RuntimeGenerator.node_manager_header())
        (output_dir / "main_template.hpp").write_text(RuntimeGenerator.main_template_header())

        _log.info("Generated headers in %s", output_dir)
