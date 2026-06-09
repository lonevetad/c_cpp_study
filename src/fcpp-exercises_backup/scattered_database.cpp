// Copyright © 2021 Giorgio Audrito. All Rights Reserved.

// CREATO A PARTIRE DAL PROGETTO "fcpp-exercises" PER STUDIARE

/**
 * @file exercises.cpp
 * @brief Quick-start aggregate computing exercises.
 */

// [INTRODUCTION]
//! Importing the FCPP library.
#include "lib/fcpp.hpp"
#include "run/shared.hpp"
#include "run/storage_init.hpp"

using s_db_key = fcpp::device_t; // the "key" part of the key-value mapping implementing a "scattered database"
using s_db_data = fcpp::vec<2>;  // the "value" part of the key-value mapping implementing a "scattered database"

/**
 @param enable Boolean stating whether it should be allow multiple queries or not
 template<int enable = 2>
 class scattered_db_query;
 */

/*
//! @brief Struct representing a data to be retrieved from a scattered database.
template<>
class scattered_db_query<true> {
  public:
    //! @brief the database KEY
    s_db_key key;
    //! @brief Receiver UID, the device/node who started this query
    fcpp::device_t requester;
    //! @brief Creation timestamp, but in "ticks".
    uint created_at_tick;
    //! @brief Creation timestamp.
    fcpp::times_t time;
    //! @brief counter, tracking how many times the device/node has asked for _some_ data
    // uint;

    //! @brief Empty constructor.
    scattered_db_query() = default;

    //! @brief Member constructor.
    scattered_db_query(
        s_db_key key,
        fcpp::device_t requester,
        uint created_at_tick,
        fcpp::times_t time
    ) : key(key), requester(requester), created_at_tick(created_at_tick), time(time) {}

    //! @brief Equality operator.
    bool operator==(scattered_db_query const& m) const {
        return key == m.key
            and requester == m.requester
            // and ... (allow_multiple_queries or ...)
            ;
    }

    //! @brief Hash computation.
    size_t hash() const {
        constexpr size_t fields_count = 4;
        constexpr size_t offs = sizeof(size_t)*CHAR_BIT/fields_count;
        size_t partial = //
            ((size_t(requester) << offs))
            | (size_t(key))
            // beware of "infinite" stream of messages
            | ((size_t(time) << (3*offs)))
            | ((size_t(created_at_tick) << (offs << 1)))
            ;
        // removed to avoind "infinite" stream of messages
        return partial;
    }

    //! @brief Serialises the content from/to a given input/output stream.
    template <typename S>
    S& serialize(S& s) {
        return s & key & requester & created_at_tick & time;
    }

    //! @brief Serialises the content from/to a given input/output stream (const overload).
    template <typename S>
    S& serialize(S& s) const {
        return s << key << requester << created_at_tick << time;
    }
};
*/

//! @brief Struct representing a data to be retrieved from a scattered database.
//template<>
class scattered_db_query/*<false>*/ {
  public:
    //! @brief the database KEY
    s_db_key key;
    //! @brief Receiver UID, the device/node who started this query
    fcpp::device_t requester;
    //! @brief Creation timestamp, but in "ticks".
    uint created_at_tick;
    //! @brief Creation timestamp.
    fcpp::times_t time;
    //! @brief counter, tracking how many times the device/node has asked for _some_ data
    // uint;

    //! @brief Empty constructor.
    scattered_db_query() = default;

    //! @brief Member constructor.
    scattered_db_query(
        s_db_key key,
        fcpp::device_t requester,
        uint created_at_tick,
        fcpp::times_t time
    ) : key(key), requester(requester), created_at_tick(created_at_tick), time(time) {}

    //! @brief Equality operator.
    bool operator==(scattered_db_query const& m) const {
        return key == m.key
            and requester == m.requester
            and(
                // ...  allow_multiple_queries is false
                // or
                // beware of "infinite" stream of messages
                created_at_tick == created_at_tick
                and time == m.time
            )
            ;
    }

    //! @brief Hash computation.
    size_t hash() const {
        constexpr size_t fields_count = 2;
        constexpr size_t offs = sizeof(size_t)*CHAR_BIT/fields_count;
        size_t partial = //
            ((size_t(requester) << offs))
            | (size_t(key))
            ;
        // removed to avoind "infinite" stream of messages
        return partial;
    }

    //! @brief Serialises the content from/to a given input/output stream.
    template <typename S>
    S& serialize(S& s) {
        return s & key & requester & created_at_tick & time;
    }

    //! @brief Serialises the content from/to a given input/output stream (const overload).
    template <typename S>
    S& serialize(S& s) const {
        return s << key << requester << created_at_tick << time;
    }

    //! @brief Returns a compact human-readable string representation.
    std::string to_string() const {
        char buf[32];
        std::snprintf(buf, sizeof(buf), "%.3g", (double)time);
        return "db_qry{key=" + std::to_string(key)
            + " r=" + std::to_string(requester)
            + " ct=" + std::to_string(created_at_tick)
            + " ts=" + buf
            + "}";
    }
};


//! @brief Struct representing a data to be retrieved from a scattered database.
struct scattered_db_response {
    //! @brief the database KEY
    s_db_key key;
    //! @brief THE ACTUAL DATA
    s_db_data data;
    //! @brief Receiver UID, the device/node who started this query
    fcpp::device_t requester;
    //! @brief Replier UID, the device/node holding this query's response data
    fcpp::device_t holder;
    //! @brief Response's creation timestamp, but in "ticks".
    uint created_at_tick;
    //! @brief Response's creation timestamp.
    fcpp::times_t time;
    //! @brief counter, tracking how many times the device/node has asked for _some_ data
    // uint;

    //! @brief Empty constructor.
    scattered_db_response() = default;

    //! @brief Member constructor.
    scattered_db_response(
        s_db_key key,
        s_db_data data,
        fcpp::device_t requester,
        fcpp::device_t holder,
        uint created_at_tick,
        fcpp::times_t time
    ) : key(key), data(data), requester(requester), holder(holder), created_at_tick(created_at_tick), time(time) {}

    //! @brief Equality operator.
    bool operator==(scattered_db_response const& m) const {
        return key == m.key
            and data == m.data
            and requester == m.requester
            and holder == m.holder
            // removed to avoind "infinite" stream of messages
            // and created_at_tick == created_at_tick
            // and time == m.time
            ;
    }

    static size_t hash(s_db_data data_to_hash){
        constexpr size_t fields_count = 2;
        constexpr size_t offs = sizeof(size_t)*CHAR_BIT/fields_count;
        return (size_t(data_to_hash[1]) << offs) | size_t(data_to_hash[0]);
    }

    //! @brief Hash computation.
    size_t hash() const {
        constexpr size_t fields_count = 4;
        constexpr size_t offs = sizeof(size_t)*CHAR_BIT/fields_count;
        return  //((size_t(time) << (5*offs))
            // (size_t(created_at_tick) << (offs << 2))
            // removed to avoind "infinite" stream of messages
            ((size_t(holder) << (3*offs)))
            | ((size_t(requester) << (offs << 1)))
            | (hash(data) << offs)
            | (size_t(key));
    }

    //! @brief Serialises the content from/to a given input/output stream.
    template <typename S>
    S& serialize(S& s) {
        return s & key & data & requester & holder & created_at_tick & time;
    }

    //! @brief Serialises the content from/to a given input/output stream (const overload).
    template <typename S>
    S& serialize(S& s) const {
        return s << key << data << requester << holder << created_at_tick << time;
    }

    //! @brief Returns a compact human-readable string representation.
    std::string to_string() const {
        char buf[32];
        auto f3 = [&](double v) -> std::string {
            std::snprintf(buf, sizeof(buf), "%.3g", v);
            return buf;
        };
        return "db_res{key=" + std::to_string(key)
            + " d=(" + f3(data[0]) + "," + f3(data[1]) + ")"
            + " r=" + std::to_string(requester)
            + " h=" + std::to_string(holder)
            + " ct=" + std::to_string(created_at_tick)
            + " ts=" + f3(time)
            + "}";
    }
};


namespace std {
    //! @brief Hasher object for the scattered_db_query struct.
    template <>
    struct hash<scattered_db_query> {
        //! @brief Produces an hash for a scattered_db_query, combining its instance variables into a size_t.
        size_t operator()(scattered_db_query const& m) const {
            return m.hash();
        }
    };

    //! @brief Hasher object for the scattered_db_response struct.
    template <>
    struct hash<scattered_db_response> {
        //! @brief Produces an hash for a scattered_db_response, combining its instance variables into a size_t.
        size_t operator()(scattered_db_response const& m) const {
            return m.hash();
        }
    };
}




/**
 * @brief Namespace containing all the objects in the FCPP library.
 */
namespace fcpp {

//! @brief Namespace containing tnode_data_requestedhe libraries of coordination routines.
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

    // 
    struct node_scattered_db {};
    struct node_current_tick {};
    struct node_data_requested {}; // turns true only if the request or its response is "travelling" (i.e., after the spawn start and no longer the spawn has ended)
    struct node_last_requested_data {};
    struct node_requests_got {};
    struct node_requests_got_amount {};
    struct node_data_got {};
    struct node_responses_provided {};
    struct node_responses_provided_str {};
}

//! @brief The maximum communication range between nodes.
constexpr size_t communication_range = 100;

constexpr bool ALLOW_MULTIPLE_QUERIES = false;

//

using scattered_db_complex_t = std::map<s_db_key, s_db_data>;

using set_nodes_to_source_t = std::set<device_t>;

using spawn_res_query = tuple<
    scattered_db_query, // original query
    bool, // has the data?
    s_db_data // the actual data
>;
using spawn_res_response = scattered_db_response; // just an alias for future developments

// map< key , returned_thing , hash >
using spawn_res_query_map = std::unordered_map<scattered_db_query, spawn_res_query, common::hash<scattered_db_query> >;
using spawn_res_response_map = std::unordered_map<spawn_res_response, scattered_db_response, common::hash<spawn_res_response> >;

using provided_responses_k = tuple<
    device_t, // sender
    s_db_key,
    uint // "created at" time tick - valorized if ALLOW_MULTIPLE_QUERIES is true, set to 0 otherwise
>;
using responses_provided_t = std::unordered_map<provided_responses_k, scattered_db_response, common::hash<provided_responses_k> >;

/*
UTILITY FUNCTIONS
*/

/**
Dummy function to test if current node is enabled to ask for some data, or if its purpose
will always be the "forwarding node"
*/
FUN bool is_node_enabled_to_request_data(ARGS){
    return node.uid == 7; // un nodo a caso ...
}

/**
Dummy function that check if current node has the need to request data.
It's "dummy" because it simply checks the timer's "current tick"
 */
FUN bool is_there_need_to_request_data(ARGS, uint current_tick){
    return is_node_enabled_to_request_data(CALL) //
        && ((current_tick % 13) == 0) // un intervallo di tempo a caso ...
        && (!(node.storage(tags::node_data_requested{})));
}


using update_key_data = tuple<
    uint, // the actual delta
    uint  // tick of last update (to avoid increments greater than 1)
>;
FUN s_db_key compute_key_query(ARGS, uint round_tick, bool can_fire_request_data){
    update_key_data delta_data = old(CALL, 
        static_cast<update_key_data>(make_tuple(0, 0)),
        [&](update_key_data const& old_update_data){
            if(can_fire_request_data &&
                (round_tick != get<1>(old_update_data))
            ){
                // an actual update may happen
                return static_cast<update_key_data>(make_tuple(get<0>(old_update_data) +1, round_tick));
            }
            return old_update_data;
        }
    );
    uint delta = get<0>(delta_data);
    auto md_id = (node.uid + delta);  // un nodo a caso ...
    while(md_id >= static_cast<s_db_key>(option::node_num)){ // module operator, but shorter
        md_id -= static_cast<s_db_key>(option::node_num);
    }
    return md_id;
}
FUN_EXPORT compute_key_query_t = export_list<update_key_data>;

/*
AGGREGATE FUNCTIONS
*/

/*
FUN device_t get_parent_spanning_tree(ARGS, real_t distance_from_source) { CALL
    return get<1>(
        min_hood(CALL,
            make_tuple(
                nbr(CALL, distance_from_source),
                node.nbr_uid()
            )
        )responses_provided_t
    );
}
EXPORT_FUN get_parent_spanning_tree_t = export_list<tuple<real_t, device_t>, device_t>;
*/

FUN void execute_scattered_db_query(ARGS, 
    uint round_tick,
    bool is_enabled_to_request
){ CODE
    //
    // COMPUTATION OF THE DATA RETRIEVAL
    //

    // Every node uses this gradient for spawn routing.
    // In a production deployment, each requester would build its own gradient,
    real_t dist_from_requester = abf_distance(CALL, is_enabled_to_request);

    // ... spanning tree definition ...

    // device_t parent = get_parent_spanning_tree(CALL, dist_from_requester);
    
    // Collects the set of UIDs in this node's spanning-tree subtree toward
    // the root.  Used to determine INTERNAL routing status for the spawn.
    // ((routing sets along the tree))
    set_nodes_to_source_t nodes_to_source = sp_collection(CALL, 
        dist_from_requester, // distance from source
        set_nodes_to_source_t{node.uid}, // set for current node
        set_nodes_to_source_t{}, // set to accumulate into
        // accumulator / aggregator function
        [](set_nodes_to_source_t a, set_nodes_to_source_t b){ a.insert(b.begin(), b.end()); return a; }
    );

    // START THE SPAWN PART

    // part 1 - query : REQUESTER -> DATA HOLDER
    
    // ... define the query
    common::option<scattered_db_query> query; // starts by "absent / nullptr-containing". filled if a "spawn-process" needs to spawn
    bool can_fire_request_data = is_there_need_to_request_data(CALL, round_tick);
    s_db_key next_key_request = compute_key_query(CALL, round_tick, can_fire_request_data);
    if(can_fire_request_data) {
        //const bool allow_multiple_queries = false;
        query.emplace(
            next_key_request, // key
            node.uid, // requester
            round_tick, //
            node.current_time() //
        );
        // later, in the spawn, the "node_data_requested" storage field will be set to "true"
    }   

    // ... run the spawn
    spawn_res_query_map query_res = spawn(CALL, [&](scattered_db_query const& message_query) {
        s_db_key key = message_query.key;
        bool is_requester = node.uid == message_query.requester;
        bool has_data = node.storage(tags::node_scattered_db{}).count(key) > 0;
        if(is_requester){
            node.storage(tags::node_data_requested{}) = true;
            node.storage(tags::node_last_requested_data{}) = message_query.to_string(); // message_query;
        }
        // bool inpath = nodes_to_source.count(message_query.from) + nodes_to_source.count(m.to) > 0;
        status s = has_data ? status::terminated_output
                : status::internal;
        if(!is_requester){
            if(has_data){
                node.storage(tags::node_size{}) = 25;
                node.storage(tags::node_shape{}) = shape::icosahedron;
            } else {
                node.storage(tags::node_size{}) = 20;
            }
        }
        return make_tuple(
            static_cast<spawn_res_query>(make_tuple(
                message_query,
                has_data,
                has_data ? (node.storage(tags::node_scattered_db{})[key]) : static_cast<s_db_data>(node.position())
            )),
            s
        );
    }, query);

    // part 2 - response : DATA HOLDER -> REQUESTER

    /*
    common::option<s_db_data> query_result;
    // if current node has a request (i.e., the map returned by the spawn has a "useful" value) ->
    // -> query_result.emplace( the answer's data -> node.storage(tags::node_scattered_db{})[ query.key ] );
    using reply_key_t = fcpp::tuple<device_t, s_db_data>;  // (querier_id, snapshot_data)
    
    bool reply_started = old(CALL, false, [&](bool prev){ return prev || q_res.count(my_key) > 0; });
    common::option<reply_key_t> reply;
    if (q_res.count(my_key) > 0 && !reply_started)
        reply.emplace(make_tuple(querier_id, node.position()));  // snapshot now
    */

    common::option<scattered_db_response> reply;
    // reply to all requests received ...
    uint greatest_requests_got_amount = old(CALL, static_cast<uint>(0),
        [&](uint x){
            return x > static_cast<uint>(query_res.size())
                ? x
                : static_cast<uint>(query_res.size());
        }
    );
    node.storage(tags::node_requests_got_amount{}) = greatest_requests_got_amount;

    // PHASE A — pure logic, no FCPP primitives.
    // Iterate query_res to decide which responses to inject; collect them into a vector.
    // Calling spawn inside this loop would be wrong: nodes with 0 entries would call it
    // 0 times while nodes with N entries call it N times, breaking trace synchronization.
    std::vector<scattered_db_response> responses_to_inject;
#if __cplusplus <= 201402L
    // C++14 and older
    for (auto const& kv : query_res) {
        scattered_db_query k = kv.first;
        spawn_res_query    v = kv.second;
#else
    // C++17 and newer
    for (auto const& [k, v] : query_res) {
#endif
        node.storage(tags::node_requests_got{})[std::to_string(k.key)] = k.to_string();
        device_t sender          = k.requester;
        s_db_key requested_key   = k.key;
        uint response_created_at = ALLOW_MULTIPLE_QUERIES ? round_tick : 0;
        bool has_data            = get<1>(v);
        s_db_data actual_data    = get<2>(v);

        provided_responses_k key_already = make_tuple(sender, requested_key, response_created_at);
        if (has_data &&
            node.storage(tags::node_responses_provided{}).count(key_already) == 0) {

            scattered_db_response resp(requested_key, actual_data,
                                       sender, node.uid, round_tick, node.current_time());
            node.storage(tags::node_responses_provided{})[key_already] = resp;
            node.storage(tags::node_responses_provided_str{})[std::to_string(requested_key)] = resp.to_string();
            responses_to_inject.push_back(resp);
        }
    }

    // PHASE B — single spawn call, outside any loop.
    // Every node reaches this point exactly once per round regardless of query_res size,
    // keeping the CALL trace counter synchronized across the network.
    // Each entry in responses_to_inject starts a separate spawn process.
    spawn_res_response_map response_res = spawn(CALL, [&](scattered_db_response const& the_final_response) {
        device_t requester = the_final_response.requester;
        bool is_requester = node.uid == requester;
        /*
        real_t dist_from_replier = abf_distance(CALL, node.uid == requester);
        set_nodes_to_source_t nodes_to_replier = sp_collection(CALL,
            dist_from_replier,
            set_nodes_to_source_t{node.uid},
            set_nodes_to_source_t{},
            [](set_nodes_to_source_t a, set_nodes_to_source_t b){ a.insert(b.begin(), b.end()); return a; }
        );
        */
        bool in_path = nodes_to_source.count(the_final_response.holder) // nodes_to_replier
            +
            nodes_to_source.count(requester) // nodes_to_replier
            > 0;
        status s = is_requester ? status::terminated_output
                : in_path ? status::internal : status::border;
        if (!is_requester) {
            node.storage(tags::node_shape{}) = in_path ? shape::sphere : shape::cube;
        }
        return make_tuple(the_final_response, s);
    }, responses_to_inject);

    // PHASE C — consume responses, pure logic, no FCPP primitives.
#if __cplusplus <= 201402L
    // C++14 and older
    for (auto const& kv : response_res) {
        auto k_r = kv.first;
        auto v_r = kv.second;
#else
    // C++17 and newer
    for (auto const& [k_r, v_r] : response_res) {
#endif
        s_db_data response_data = v_r.data;
        device_t requester      = v_r.requester;
        s_db_key request_key    = v_r.key;
        if (node.uid == requester) {
            node.storage(tags::node_data_got{})[k_r.to_string()] = response_data;
            if (node.storage(tags::node_scattered_db{}).count(request_key) == 0) {
                node.storage(tags::node_scattered_db{})[request_key] = response_data;
            }
            node.storage(tags::node_data_requested{}) = false;
        } else {
            node.storage(tags::node_last_requested_data{}) = "AM I NOT THE REQUESTER? <" +
                std::to_string(node.uid) + " ; " + std::to_string(requester) + ">";
        }
    }
}
FUN_EXPORT execute_scattered_db_query_t = export_list<
    // get_parent_spanning_tree_t,
    compute_key_query_t,
    real_t,
    uint,
    set_nodes_to_source_t,
    sp_collection_t<real_t, set_nodes_to_source_t>, 
    device_t,
    abf_distance_t,
    spawn_t<scattered_db_query, status>,
    spawn_t<spawn_res_response, status>
>;

//
//



FUN void initialize_scattered_db(ARGS){ CODE
    auto scattered_database_result = // new_vector_coprime_IDs(CALL);
        old(CALL,
            scattered_db_complex_t{}, // default at round 0
            [&](scattered_db_complex_t const& old_data){
                scattered_db_complex_t new_data = new_coprime_nbr_data(CALL, [&](node_t const& neighbor){ return static_cast<s_db_data>(neighbor.position()); });
                // keep the first initialization, i.e. never update iit
                return old_data.empty() ? new_data : old_data; 
            }
        );
    node.storage(tags::node_scattered_db{}) = scattered_database_result;
}
FUN_EXPORT initialize_scattered_db_t = export_list<scattered_db_complex_t, new_coprime_nbr_data_t, s_db_data>;

// @brief Main function.
MAIN() {
    //
    // import tag names in the local scope.
    using namespace tags;
    
    uint round_tick = old(CALL, 0, [&](uint a){
        return a+1;
    });
    //
    node.storage(node_current_tick{}) = round_tick;
    
    // initialization
    initialize_scattered_db(CALL);
    
    // THE ACTUAL CODE
        
    /*
    in futuro, ci saranno più nodi contemporaneamente a fare richieste -> ciascuno con il proprio ... spawn? forse?
    */
    bool is_enabled_to_request = is_node_enabled_to_request_data(CALL);


    // usage of node physics
    //node.velocity() = -node.position()/communication_range;

    auto constexpr maximum_db_size = 15.0f;
    // usage of node storage
    node.storage(node_size{}) = is_enabled_to_request ? 30 : 10;
    auto constexpr hue_scale = 360.0f / maximum_db_size; // option::node_num;
    node.storage(node_color{}) = //
        color::hsva( static_cast<real_t>(node.storage(node_scattered_db{}).size()) * hue_scale, 1, 1);

    if(is_enabled_to_request){
        node.storage(node_shape{}) = shape::star; // is_enabled_to_request ? shape::star : shape::sphere; // icosahedron
    } else {
        node.storage(node_shape{}) = shape::tetrahedron;
    }

    // DO THE THING

    execute_scattered_db_query(CALL,
        round_tick,
        is_enabled_to_request
    );

        
}
    
//! @brief Export types used by the main function (update it when expanding the program).
FUN_EXPORT main_t = export_list<
    initialize_scattered_db_t,
    uint,
    // bool, // it's not actually shared across the nodes
    new_coprime_nbr_data_t, // new_vector_coprime_IDs_t,
    old_t<scattered_db_complex_t>, // old_t<new_vector_coprime_IDs_t>
    scattered_db_complex_t, 
    execute_scattered_db_query_t
>;

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
    , node_scattered_db,        coordination::scattered_db_complex_t // vector_coprime_IDs_t

    , node_data_requested,      bool
    , node_last_requested_data, std::string // scattered_db_query
    , node_current_tick,        uint
    , node_requests_got,        std::map<std::string, std::string>
    , node_requests_got_amount, uint
    , node_data_got,            std::map<std::string, s_db_data> // s_db_data
    , node_responses_provided,  coordination::responses_provided_t 
    , node_responses_provided_str, std::map<std::string, std::string> 
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

// cd fcpp-exercises
// ./make.sh gui run -O scattered_database
