#include <fcpp/fcpp.hpp>


// Generated compute helper (transpiled from Python)
double compute_next_state(
    const double& self_state,
    const std::vector<double>& neighbor_states) {
    if ((!neighbor_states.values)) {
        return self_state;
    }
    return std::max(self_state, std::max(neighbor_states.values));
}



// Generated FCPP aggregate program — ConsensusAggregate
namespace fcpp_generated {

AGGREGATE_TEMPLATE(main) : void {
    using state_t = double;

    // Initialize or retrieve persistent state
    auto& current_state = old(CALL, static_cast<state_t>(random.uniform(0.0, 100.0)));

    // Collect neighbor states via nbr
    auto nbr_states = nbr(CALL, current_state);

    // Flatten field to vector for compute helper
    std::vector<state_t> neighbor_vec;
    fold_hood(CALL, [&](state_t v, fcpp::unit) {
        neighbor_vec.push_back(v);
        return fcpp::unit{};
    }, fcpp::unit{}, nbr_states);

    // Compute next state from transpiled Python logic
    current_state = compute_next_state(current_state, neighbor_vec);
}

}  // namespace fcpp_generated

// Entry point — spawns IPC server then runs simulation
int main(int argc, char* argv[]) {
    int num_nodes = (argc > 1) ? std::atoi(argv[1]) : 100;
    int ipc_port  = (argc > 2) ? std::atoi(argv[2]) : 8765;

    // TODO: initialise FCPPSimulator with num_nodes and ipc_port
    return 0;
}
