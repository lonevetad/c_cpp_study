// Generic fcpp simulation bridge with Python per-round callbacks.
//
// Architecture: C++ handles network topology, round scheduling, and neighbor
// message-passing. Python defines per-round logic via a callback.
//
// Drone state = std::array<double, STATE_SIZE>.
// Python maps ANY class/tuple to doubles; the bridge is agnostic.

#include <array>
#include <cstdint>
#include <cstring>
#include <limits>
#include <vector>

// vec_vararg.hpp must be first: provides explicit vec<N> specializations with
// element-wise constructors, restoring C++17-style brace-init in C++20+.
// Include BEFORE any fcpp header that triggers vec instantiation.
#include "vec_vararg.hpp"

// Selective fcpp includes — avoids lib/simulation.hpp which pulls in
// lib/simulation/displayer.hpp (OpenGL) and breaks headless Linux builds.
// Also excludes simulated_map (requires stbi image loading) as it's not needed
// for headless simulation computation.
#include "lib/component.hpp"
#include "lib/coordination/basics.hpp"
#include "lib/data.hpp"
#include "lib/settings.hpp"
#include "lib/beautify.hpp"
#include "lib/simulation/simulated_connector.hpp"
#include "lib/simulation/simulated_positioner.hpp"
#include "lib/simulation/spawner.hpp"

using namespace fcpp;
using namespace component::tags;

// ── Compile-time parameters (override via Makefile: make DEVICES=50 all) ──

#ifndef FCPP_PY_DEVICES
#define FCPP_PY_DEVICES 100
#endif
#ifndef FCPP_PY_SIDE
#define FCPP_PY_SIDE 200
#endif
#ifndef FCPP_PY_HEIGHT
#define FCPP_PY_HEIGHT 10
#endif
#ifndef FCPP_PY_COMM
#define FCPP_PY_COMM 50
#endif
#ifndef FCPP_PY_DIM
#define FCPP_PY_DIM 3
#endif
#ifndef FCPP_PY_STATE_SIZE
#define FCPP_PY_STATE_SIZE 8
#endif

constexpr int DEVICES = FCPP_PY_DEVICES;
constexpr int SIDE = FCPP_PY_SIDE;
constexpr int HEIGHT = FCPP_PY_HEIGHT;
constexpr int COMM = FCPP_PY_COMM;
constexpr int DIM = FCPP_PY_DIM;
constexpr int STATE_SIZE = FCPP_PY_STATE_SIZE;

// ── Per-device state type ──────────────────────────────────────────────────
// Fixed-size double array. Python maps any class/tuple to this via
// to_doubles() / from_doubles().
using state_t = std::array<double, STATE_SIZE>;

// ── Python callback signature ──────────────────────────────────────────────
// Called once per device per simulation round.
//
//   device_id        — uint ID of the device being updated
//   current_time     — simulation time of this round
//   self_prev        — STATE_SIZE doubles: this device's exported state from
//                      the previous round (zeros on first round)
//   neighbor_ids     — array of neighbor device IDs, length = neighbor_count
//   neighbor_states  — neighbor_count * STATE_SIZE doubles (row-major):
//                      neighbor_states[i*STATE_SIZE .. (i+1)*STATE_SIZE-1]
//                      = exported state of neighbor_ids[i] last round
//   neighbor_count   — number of current neighbors
//   result_out       — write STATE_SIZE doubles here: new exported state
//
// Caution: callback must be thread-safe if DEVICES is large and fcpp uses
// parallel rounds (parallel<false> is set here, so single-threaded).
extern "C"
{
    using fcpp_round_cb_t = void (*)(
        int32_t device_id,
        double current_time,
        const double *self_prev,
        const int32_t *neighbor_ids,
        const double *neighbor_states,
        int32_t neighbor_count,
        double *result_out);
}

static fcpp_round_cb_t g_round_callback = nullptr;

// ── Per-node storage tags ─────────────────────────────────────────────────
namespace sim_tags
{
    struct exported_state
    {
    }; // last exported state, readable via C ABI
    struct position
    {
    }; // Vec3 position snapshot (3 doubles)
}

// ── MAIN — defined as struct (not via MAIN() macro) to name the time param ─
// This is equivalent to what MAIN() would generate but gives access to `t`.
namespace fcpp
{
    namespace coordination
    {

        struct main
        {
            template <typename node_t>
            void operator()(node_t &node, times_t t)
            {

                state_t zero{}; // default: all 0.0

                // nbr(CALL, init, f): exchange state with neighbors.
                //   - exports f(nbr_field) to neighbors each round
                //   - on entry: nbr_field contains what each neighbor exported last round
                //   - self(nbr_field, node.uid) = what THIS device exported last round
                //                                 (zero on first round)
                state_t result = nbr(CALL, zero,
                                     [&](field<state_t> nbr_field) -> state_t
                                     {
                                         // Self's previous exported value
                                         state_t self_prev = fcpp::details::self(nbr_field, node.uid);

                                         // Neighbor IDs and their states (vals[0]=default, vals[i+1]=ids[i])
                                         auto const &nbr_ids = fcpp::details::get_ids(nbr_field);
                                         auto const &nbr_vals = fcpp::details::get_vals(nbr_field);

                                         int32_t n = static_cast<int32_t>(nbr_ids.size());

                                         state_t out{};

                                         if (g_round_callback)
                                         {
                                             // Build contiguous C arrays for the callback
                                             std::vector<int32_t> ids_c(n);
                                             std::vector<double> states_c(static_cast<size_t>(n) * STATE_SIZE);

                                             for (int32_t i = 0; i < n; ++i)
                                             {
                                                 ids_c[i] = static_cast<int32_t>(nbr_ids[i]);
                                                 const state_t &ns = nbr_vals[static_cast<size_t>(i) + 1];
                                                 for (int j = 0; j < STATE_SIZE; ++j)
                                                     states_c[static_cast<size_t>(i) * STATE_SIZE + j] = ns[j];
                                             }

                                             g_round_callback(
                                                 static_cast<int32_t>(node.uid),
                                                 static_cast<double>(t),
                                                 self_prev.data(),
                                                 ids_c.data(),
                                                 states_c.data(),
                                                 n,
                                                 out.data());
                                         }
                                         return out;
                                     });

                node.storage(sim_tags::exported_state{}) = result;
            }
        };

        // Export type: the array that devices exchange with neighbors
        FUN_EXPORT main_t = export_list<state_t>;

    }
} // namespace fcpp::coordination

// ── Headless simulator: batch_simulator without displayer ─────────────────
// Equivalent to fcpp::component::batch_simulator but does NOT include the
// displayer component → no OpenGL dependency → works on headless Linux.
namespace fcpp
{
    namespace component
    {

        DECLARE_COMBINE(headless_simulator,
                        simulated_connector, simulated_positioner,
                        timer, scheduler, logger, storage, spawner, identifier,
                        randomizer, calculus);

    }
} // namespace fcpp::component

// ── Simulation options ────────────────────────────────────────────────────
using round_s = sequence::periodic<
    distribution::interval_n<times_t, 0, 1>,
    distribution::weibull_n<times_t, 10, 1, 10>>;

DECLARE_OPTIONS(sim_opt,
                parallel<false>,
                synchronised<false>,
                program<coordination::main>,
                exports<coordination::main_t>,
                round_schedule<round_s>,
                spawn_schedule<sequence::multiple_n<DEVICES, 0>>,
                tuple_store<
                    sim_tags::exported_state, state_t>,
                init<x, distribution::rect_n<1, 0, 0, 0, SIDE, SIDE, HEIGHT>>,
                dimension<DIM>,
                connector<connect::fixed<COMM, 1, DIM>>);

// ── SimNet: subclass exposes protected node iterators ────────────────────
// fcpp's identifier component keeps node iterators as protected members.
// A derived class can access them directly (standard C++ protected access).
class SimNet : public component::headless_simulator<sim_opt>::net
{
public:
    using base_t = component::headless_simulator<sim_opt>::net;
    using base_t::base_t; // inherit constructors

    int32_t get_device_count() const
    {
        return static_cast<int32_t>(node_size());
    }

    // Collect device IDs (up to max_n); returns actual count.
    int32_t collect_ids(int32_t *ids_out, int32_t max_n) const
    {
        int32_t n = 0;
        for (auto it = node_begin(); it != node_end() && n < max_n; ++it, ++n)
            ids_out[n] = static_cast<int32_t>(it->first);
        return n;
    }

    // Read exported state of one device. Returns false if not found.
    bool get_state(device_t uid, double *out) const
    {
        for (auto it = node_begin(); it != node_end(); ++it)
        {
            if (it->first == uid)
            {
                const state_t &s = it->second.storage<sim_tags::exported_state>();
                std::memcpy(out, s.data(), STATE_SIZE * sizeof(double));
                return true;
            }
        }
        return false;
    }

    // Collect all states in one call (row-major: states[i*STATE_SIZE..]).
    int32_t collect_all(int32_t *ids_out, double *states_out, int32_t max_n) const
    {
        int32_t n = 0;
        for (auto it = node_begin(); it != node_end() && n < max_n; ++it, ++n)
        {
            ids_out[n] = static_cast<int32_t>(it->first);
            const state_t &s = it->second.storage<sim_tags::exported_state>();
            std::memcpy(states_out + n * STATE_SIZE, s.data(), STATE_SIZE * sizeof(double));
        }
        return n;
    }
};

// ── Global simulation instance ────────────────────────────────────────────
static SimNet *g_sim = nullptr;

// ── C ABI ─────────────────────────────────────────────────────────────────
extern "C"
{

    // Compile-time constants readable from Python
    int32_t fcpp_sim_state_size() { return static_cast<int32_t>(STATE_SIZE); }
    int32_t fcpp_sim_max_devices() { return static_cast<int32_t>(DEVICES); }
    int32_t fcpp_sim_dimension() { return static_cast<int32_t>(DIM); }

    // Create simulation. Returns 0 on success, -1 on error.
    int32_t fcpp_sim_create()
    {
        try
        {
            delete g_sim;
            auto init_v = common::make_tagged_tuple<>();
            g_sim = new SimNet{init_v};
            return 0;
        }
        catch (...)
        {
            g_sim = nullptr;
            return -1;
        }
    }

    // Register the Python per-round callback (must be a plain C function pointer,
    // e.g. ctypes.CFUNCTYPE with no captures).
    void fcpp_sim_set_callback(fcpp_round_cb_t fn)
    {
        g_round_callback = fn;
    }

    // Run simulation until time >= end_time.
    void fcpp_sim_run(double end_time)
    {
        if (g_sim)
            g_sim->run(static_cast<times_t>(end_time));
    }

    // Advance exactly one scheduled event. Returns remaining time, or -1 if done.
    double fcpp_sim_step()
    {
        if (!g_sim)
            return -1.0;
        times_t nxt = g_sim->next();
        if (nxt < std::numeric_limits<times_t>::max())
        {
            g_sim->update();
            return static_cast<double>(g_sim->next());
        }
        return -1.0;
    }

    // Next scheduled event time (-1 if simulation is over).
    double fcpp_sim_next_time()
    {
        if (!g_sim)
            return -1.0;
        times_t nxt = g_sim->next();
        return (nxt < std::numeric_limits<times_t>::max()) ? static_cast<double>(nxt) : -1.0;
    }

    // Current device count.
    int32_t fcpp_sim_device_count()
    {
        return g_sim ? g_sim->get_device_count() : 0;
    }

    // Fill ids_out with device IDs. Returns count written.
    int32_t fcpp_sim_get_ids(int32_t *ids_out, int32_t max_n)
    {
        return g_sim ? g_sim->collect_ids(ids_out, max_n) : 0;
    }

    // Read exported state for one device. Returns 1 if found, 0 if not.
    int32_t fcpp_sim_get_state(int32_t uid, double *state_out)
    {
        if (!g_sim || !state_out)
            return 0;
        return g_sim->get_state(static_cast<device_t>(uid), state_out) ? 1 : 0;
    }

    // Read all device states in one call.
    // states_out must hold max_n * STATE_SIZE doubles.
    // Returns count written to ids_out / rows in states_out.
    int32_t fcpp_sim_get_all_states(int32_t *ids_out, double *states_out, int32_t max_n)
    {
        if (!g_sim || !ids_out || !states_out)
            return 0;
        return g_sim->collect_all(ids_out, states_out, max_n);
    }

    // Destroy simulation and free memory.
    void fcpp_sim_destroy()
    {
        delete g_sim;
        g_sim = nullptr;
        g_round_callback = nullptr;
    }

} // extern "C"
