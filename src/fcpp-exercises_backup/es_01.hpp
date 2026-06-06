
/**
 * @file es_01.hpp
 * @brief
 */

#ifndef FCPP_ES_01_H_
#define FCPP_ES_01_H_

#include "lib/beautify.hpp"
#include "lib/coordination.hpp"
#include "lib/data.hpp"

#include <iostream>

constexpr fcpp::real_t MAX_RANGE = 155.0;
constexpr fcpp::device_t LAST_DIGIT_UID_SPECIAL = 0;


/**
 * @brief Namespace containing all the objects in the FCPP library.
 */
namespace fcpp {

    //! @brief Namespace containing the libraries of coordination routines.
    namespace coordination {
        
        namespace tags {
            //! @brief Color of the current node.
            struct node_color {};
            
            //! @brief Shape of the current node.
            struct node_shape {};

            //! @brief Size of the current node.
            struct node_size {};

            //! @brief amount of special neighbours within a range
            struct special_in_range{};
        }


        //! @brief Main function.
        MAIN() {
            using namespace tags;
            struct unit{};

            common::option<device_t> key;
            bool isSpecial = (node.uid % 10) == LAST_DIGIT_UID_SPECIAL;

            node.storage(node_shape{}) = shape::sphere;
            node.storage(node_size{}) = 2.0;
            if (isSpecial) {
                key.emplace(node.uid);
                node.storage(node_color{}) = color(PURPLE);
            }else {
                node.storage(node_color{}) = color(GREEN);
                node.storage(special_in_range{}) = 0;
                node.storage(node_size{}) = 3.0;
            }

            std::unordered_map<device_t, unit> res = spawn(CALL,
                [&](device_t const& k){
                    status s;
                    
                    if(abf_distance(CALL, node.uid == k) < MAX_RANGE){
                        if((node.uid % 10) == LAST_DIGIT_UID_SPECIAL){ // if the node is special
                            s = status::internal_output;
                        } else {
                            s = status::internal; // keep in the process, but do not count current node as "special"
                        }
                    } else {
                        s = status::external;
                    }

                    return make_tuple( unit{}, s );
                }
                , key
            );

            if(isSpecial){
                int special_count = res.size() - 1;
                node.storage(special_in_range{}) = special_count;
                node.storage(node_size{}) = 2.0 + min(50.0, (double)(special_count << 2) );

                // DEBUG
                std::stringstream ss;

                for(auto const& x: res){
                    ss << x.first << ", ";
                }

                std::cout << "__ node : " << node.uid << " has this specials in range: " << ss.str() << std::endl;
                /*
                */
            }
        }

        //! @brief Exports for the main function.
        FUN_EXPORT main_t = common::export_list< 
            int
            , spawn_t<device_t, status>
            , abf_distance_t
            >;


        namespace option {
            //! @brief Import tags to be used for component options.
            //using namespace component::tags;
            using namespace coordination::tags;

            //! @brief Import tags used by aggregate functions.
            using namespace coordination::tags;

            using store_t = component::tags::tuple_store<
                node_color,                 color,
                node_size,                  double,
                node_shape,                 shape,
                special_in_range,           int\
            >;
        }
    }

}

#endif