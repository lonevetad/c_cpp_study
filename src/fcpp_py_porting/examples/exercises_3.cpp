// Copyright © 2021 Giorgio Audrito. All Rights Reserved.

// CREATO A PARTIRE DAL PROGETTO "fcpp-exercises" PER STUDIARE

/**
 * @file exercises.cpp
 * @brief Quick-start aggregate computing exercises.
 */

// [INTRODUCTION]
//! Importing the FCPP library.
#include "lib/fcpp.hpp"
#include "run/random_bounce.hpp"

/**
 * @brief Namespace containing all the objects in the FCPP library.
 */
namespace fcpp {

//! @brief Dummy ordering between positions (allows positions to be used as secondary keys in ordered tuples).
template <size_t n>
bool operator<(vec<n> const& v1, vec<n> const& v2) {
    int i = 0;
    while(i < n){
        auto e1 = v1[i];
        auto e2 = v2[i]; 
        if(e1 > e2){
            return false;
        } else if(e1 < e2){
            return true;
        } // else: identical
        i++;
    }
    return false;
}

//! @brief Namespace containing the libraries of coordination routines.
namespace coordination {



//! @brief Namespace for component options.
namespace option { // CONSTANTS
    //! @brief Number of people in the area.
    constexpr int node_num = 100;

    //! @brief Dimensionality of the space.
    constexpr size_t dim = 2;

    //! @brief Width of the network area (the GUI, actually).
    constexpr int network_width = 700;
    //! @brief Height of the network area (the GUI, actually).
    constexpr int network_height = 500;
    //! @brief used in "random_bounce": tolerance for approaching the desired point (5% of the mean between width and height)
    constexpr real_t maximum_movement_step = static_cast<real_t>(network_width + network_height) / 40;
    //! @brief 
    constexpr real_t period_between_bounces = 10.0;
}


//! @brief Tags used in the node storage.
namespace tags {
    //! @brief Color of the current node.
    struct node_color {};
    //! @brief Size of the current node.
    struct node_size {};
    //! @brief Shape of the current node.
    struct node_shape {};
    // ... add more as needed, here and in the tuple_store<...> option below

    //! @brief tracks the executed rounds (a progressive integer)
    struct node_rounds_done {};
    
    // 1) # o neighbour
    //! @brief count the amount of neighbors.
    struct node_nbr_amount {};
    //! @brief count the maximum amount of neighbors across self and all ouf neighbors.
    // (if self is connected to A and B, self sees 3 devices, A sees 7 and B sees 2,
    // -> this attribute will store the value 7)
    struct node_max_connections_on_neighbors {};
    
    // 2)
    struct node_max_nbr_amount {};
    
    // 3)
    struct node_max_nbr_ever {};

    // 4)
    struct node_nbr_loneliness {};
    struct node_nbr_loneliest_id {};
    struct node_nbr_loneliest_x {};
    struct node_nbr_loneliest_y {};

} 

//! @brief The maximum communication range between nodes.
constexpr size_t communication_range = 100;

using node_nbr_data_t = tuple<int, device_t, vec<option::dim>>;


// [AGGREGATE PROGRAM]

/**
 * BASE EXERCISES:
 *
 * Expand the MAIN function below to compute the following:
 *
 * 1)    The number of neighbour devices.
 *
 * 2)    The maximum number of neighbour devices ever witnessed by the current device.
 *
 * 3)    The maximum number of neighbour devices ever witnessed by any device in the network.
 *
 * 4)    Move towards the neighbour with the lowest number of neighbors.
 *
 * Every exercise above is designed to help solving the following one.
 *
 *
 * SIMULATION PHYSICS:
 *
 * 5)    Move away from the neighbour with the highest number of neighbors.
 *
 * 6)    Move as if the device was attracted by the neighbour with the lowest number of neighbors,
 *       and repulsed by the neighbour with the highest number of neighbors.
 *
 * 7)    Move as if the device was repulsed by every neighbour, and by the four walls of the
 *       rectangular box between points [0,0] and [500,500].
 *
 *
 * COMBINING SPATIAL COMPUTING BLOCKS:
 *
 * 8)   Select a node called "source", chosen by finding the node with minimum uid 
 *      in the network, assuming that the diameter of the network is no more than 10 hops.
 *
 * 9)   Compute the distances between any node and the "source" using the adaptive bellman-ford algorithm.
 *
 * 10)  Calculate in the source an estimate of the true diameter of the network
 *      (the maximum distance of a device in the network).
 *
 * 11)  Broadcast the diameter to every node in the network.
 *
 *
 * RUNTIME MONITORING:
 * 
 * Given that:
 * - the node(s) identified as "source" in exercise (8) are Internet Gateways (gateway),
 * - a node is at risk of disconnection (disrisk) iff it has less than three neighbors,
 * monitor the following properties:
 * 
 * 12)  You (the current device) have never been at disrisk.
 * 
 * 13)  In the network, there exists a node that has never been at disrisk.
 * 
 * 14)  You (the current device) can always reach a gateway through nodes that are not at disrisk.
 * 
 * 15)  You (the current device) can always reach a gateway through nodes that have never been at disrisk.
 * 
 * In order to check whether what you computed is correct, you may display the computed
 * quantities as node qualities through tags `node_color`, `node_size` and `node_shape`.
 * You can also save your computed quantities in additional specific node attributes:
 * towards this end, you should both add a tag in namespace tags above, then list it
 * (together with the corresponding data type) in the `tuple_store` option below.
 *
 * HINTS:
 *
 * -    In the first few exercises, start by reasoning on when/where to use `nbr` (collecting from
 *      neighbors) and `old` (collecting from the past).
 *
 * -    In order to move a device, you need to set a velocity vector through something like
 *      `node.velocity() = make_vec(0,0)`.
 *
 * -    Coordinates are available through `node.position()`. Coordinates can be composed as physical
 *      vectors: `[1,3] + [2,-1] == [3,2]`, `[2,4] * 0.5 == [1,2]`.
 *
 * -    In the simulation physics exercises, you can model attraction/repulsion using the classical inverse square law.
 *      More precisely, if `v` is the vector between two objects, the resulting force is `v / |v|^3` where
 *      `|v| = sqrt(v_x^2 + v_y^2)`. In FCPP, `norm(v)` is available for computing `|v|`.
 *
 * -    FCPP provides some built-in APIs, like "diameter_election" and "abf_distance". 
 *      Refer to the documentation: https://fcpp-doc.surge.sh
 */

/*
 * @brief example function for checking a property. 
 * Sample property: you (the current device) have not been at disrisk for a couple of rounds.
 */
FUN bool recent_dis_monitor(ARGS, bool disrisk) { CODE
    using namespace logic;
    bool prev_disrisk = Y(CALL, disrisk);
    return !disrisk & !prev_disrisk;
}
FUN_EXPORT monitor_t = export_list<past_ctl_t, slcs_t>;


// @brief Main function.
MAIN() {
    // import tag names in the local scope.
    using namespace tags;

    // sample code below (substitute with the solution to the exercises)...

    // usage of aggregate constructs
    //field<double> f = nbr(CALL, 4.2); // nbr with single value
    int rounds_done = old(CALL, 0, [&](int a){  // old with initial value and update function
        return a+1;
    });
    
    // START EXERCISES
    
    // 1)
    int nbr_amount = count_hood(CALL) - 1;

    // 1.2 
    /*
    int max_connections_on_neighbors = nbr(CALL, 0, [&](field<int> a){ // nbr with initial value and update function
        return max_hood(CALL, a, nbr_amount);
    });
    */
    int max_connections_on_neighbors = 0;
    nbr(CALL, 0, [&](field<int> a){ // nbr with initial value and update function
        max_connections_on_neighbors = max_hood(CALL, a, nbr_amount);
        return nbr_amount;
    });

    // 2)
    int max_nbr_amount = old(CALL, 0, [&](int a){  // old with initial value and update function
        return max(a, nbr_amount);
    });
    node.storage(node_max_nbr_amount{}) = max_nbr_amount;
    
    // 3)
    // NOTES: may use the "gossip": share the current "maximum", gather the "maximum" from neighbors, "accumulate" the maximal value and then update the "maximum" with the accumulated result
    int max_nbr_ever = old(CALL, 0, [&](int a){  // old with initial value and update function
        return max(a,
            nbr(CALL, a, [&](field<int> a){ // nbr with initial value and update function
                return max_hood(CALL, a, nbr_amount);
            })
        );
    });
    node.storage(node_max_nbr_ever{}) = max_nbr_ever;


    // usage of node physics
    //node.velocity() = -node.position()/communication_range;

    // usage of node storage
    node.storage(node_size{}) = 10;
    auto const hue_scale = 360.0f / option::node_num;
    /**
    If current device has the greatest amount of connections across itself and its neighbors, then it's a local peak (local maxima).
    It's like having the derivative equal to 0.
    */
    bool is_a_peak = (nbr_amount == max_connections_on_neighbors);
    node.storage(node_color{}) = 
        /*is_a_peak
        ? color(PURPLE)
        : 
        //color( GREEN + static_cast<int>( (static_cast<real_t>(nbr_amount) / option::dim) * static_cast<real_t>(BLUE-GREEN)) )
        */
        color::hsva( static_cast<real_t>(nbr_amount) * 4 * hue_scale, 1, 1)
    ;
    node.storage(node_shape{}) = is_a_peak ? shape::star : shape::sphere;
    node.storage(node_rounds_done{}) = rounds_done;
    // 1)
    node.storage(node_nbr_amount{}) = nbr_amount;
    node.storage(node_max_connections_on_neighbors{}) = max_connections_on_neighbors;
    

    // 2)
}
//! @brief Export types used by the main function (update it when expanding the program).
FUN_EXPORT main_t = export_list<double, int, monitor_t>;

} // namespace coordination

// [SYSTEM SETUP]

//! @brief Namespace for component options.
namespace option {

//! @brief Import tags to be used for component options.
using namespace component::tags;
//! @brief Import tags used by aggregate functions.
using namespace coordination::tags;


//! @brief Description of the round schedule.
using round_s = sequence::periodic<
    distribution::interval_n<times_t, 0, 1>,    // uniform time in the [0,1] interval for start
    distribution::weibull_n<times_t, 10, 1, 10> // weibull-distributed time for interval (10/10=1 mean, 1/10=0.1 deviation)
>;
//! @brief The sequence of network snapshots (one every simulated second).
using log_s = sequence::periodic_n<1, 0, 1>;
//! @brief The sequence of node generation events (node_num devices all generated at time 0).
using spawn_s = sequence::multiple_n<coordination::option::node_num, 0>;
//! @brief The distribution of initial node positions (random in a 500x500 square).
using rectangle_d = distribution::rect_n<1, 0, 0, coordination::option::network_width, coordination::option::network_height>;
//! @brief The contents of the node storage as tags and associated types.
using store_t = tuple_store<
    node_color,                 color,
    node_size,                  double,
    node_shape,                 shape
    //
    , node_rounds_done,         int
    , node_nbr_amount,          int // 1)
    , node_max_connections_on_neighbors, int
    , node_max_nbr_amount,      int // 2)
    , node_max_nbr_ever,        int // 3)
    // 4)
    , node_nbr_loneliness,      int
    , node_nbr_loneliest_id,    device_t
    , node_nbr_loneliest_x,     double
    , node_nbr_loneliest_y,     double
    // 5)

    , node_bounce_side,         int
    , node_bounce_x,            int
    , node_bounce_y,            int
>;
//! @brief The tags and corresponding aggregators to be logged (change as needed).
using aggregator_t = aggregators<
    node_size,                  aggregator::mean<double>
    //
    //, node_nbr_amount,          aggregator::mean<int>
>;

//! @brief The general simulation options.
DECLARE_OPTIONS(list,
    parallel<true>,      // multithreading enabled on node rounds
    synchronised<false>, // optimise for asynchronous networks
    program<coordination::main>,   // program to be run (refers to MAIN above)
    exports<coordination::main_t>, // export type list (types used in messages)
    retain<metric::retain<2,1>>,   // messages are kept for 2 seconds before expiring
    round_schedule<round_s>, // the sequence generator for round events on nodes
    log_schedule<log_s>,     // the sequence generator for log events on the network
    spawn_schedule<spawn_s>, // the sequence generator of node creation events on the network
    store_t,       // the contents of the node storage
    aggregator_t,  // the tags and corresponding aggregators to be logged
    init<
        x,      rectangle_d // initialise position randomly in a rectangle for new nodes
    >,
    dimension<coordination::option::dim>, // dimensionality of the space
    connector<connect::fixed<coordination::option::node_num, 1, coordination::option::dim>>, // connection allowed within a fixed comm range
    shape_tag<node_shape>, // the shape of a node is read from this tag in the store
    size_tag<node_size>,   // the size  of a node is read from this tag in the store
    color_tag<node_color>  // the color of a node is read from this tag in the store
    //
    //, nbr_amount_tag<node_nbr_amount>
    // , node_rounds_done
);

} // namespace option

} // namespace fcpp


//! @brief The main function.
int main() {
    using namespace fcpp;
    
    //! @brief The network object type (interactive simulator with given options).
    using net_t = component::interactive_simulator<option::list>::net;
    //! @brief The initialisation values (simulation name).
    auto init_v = common::make_tagged_tuple<option::name>("Exercises");
    //! @brief Construct the network object.
    net_t network{init_v};
    //! @brief Run the simulation until exit.
    network.run();
    return 0;
}

// ./make.sh gui run -O exercises
