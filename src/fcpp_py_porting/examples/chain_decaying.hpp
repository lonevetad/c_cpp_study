
/**
 * @file chain_decaying.hpp
 * @brief
 */

#ifndef FCPP_CHAIN_DECAYING_H
#define FCPP_CHAIN_DECAYING_H

#include "lib/beautify.hpp"
#include "lib/coordination.hpp"
#include "lib/data.hpp"


#include <iostream>
#include <stdlib.h>
#include <stdio.h>



/**
 * @brief Namespace containing all the objects in the FCPP library.
 */
namespace fcpp
{
    //! @brief Namespace containing the libraries of coordination routines.
    namespace coordination
    {

        constexpr int inf_int = 2147483647; // (int)(( ((unsigned long)1)<<31)-1);

        namespace tags
        {
            //! @brief Color of the current node.
            struct node_color
            {
            };
            

            //! @brief Shape of the current node.
            struct node_shape
            {
            };

            //! @brief Size of the current node.
            struct size
            {
            };

            struct id{
            };

            //! @brief Color of the current node.
            struct in_channel
            {
            };
            
        } // namespace tags


        template<typename D = int> using decaying_node_data = tuple<
            bool, // should I NOT increment the TTL?
            int, // hops count
            D // TTL
            , device_t // next node, closer to the source
        >;

        // Le estremita' della catena (che potrebbero pero' essere nel mezzo, il tutto si adatta) continuano
        // a "rinfrescare" la catena, mentre gli altri nodi tendono a farla "degradare"
        // (incrementando un TTL, cioe' un contatore "Time To Live").
        // Appena un nodo non e' rinfrescato da abbastanza tempo (cioe' il TTL eccede)
        template<typename node_t, typename D = int,
            typename M, typename = common::if_signature<M, D(node_t&, device_t)>,
            typename R, typename = common::if_signature<R, D(node_t&, decaying_node_data<D>)>
        > bool is_alive_decaying( ARGS, bool is_chain_extremity, bool was_on_chain, D infinite_value, M&& distance_metric, R&& threshold_TTL_getter){
            CODE

            constexpr D error_ttl = (D) -1;

            was_on_chain |= is_chain_extremity;

            decaying_node_data<D> data = nbr (CALL,
                make_tuple(
                    ! is_chain_extremity,
                    is_chain_extremity ? 0 : inf_int,
                    (D)(is_chain_extremity ? 0 : -1) // "-1" == "give enough time to the fartest nodes"
                    , node.uid
                ),
                [&](field<decaying_node_data<D>> d){
                    bool has_to_increment = false, am_I_closest;
                    decaying_node_data<D> n, myself; // "n" = nearest to the source
                
                    myself = fcpp::details::self(d, node.uid);
                    n = min_hood(CALL, d);

                    if( ! was_on_chain ) {
                        // error
                        return make_tuple(false, 0, error_ttl , node.uid
                        );
                    }

                    if( is_chain_extremity ){
                        return make_tuple(false, 0, (D)0 , node.uid
                        );
                    } //regenerate the tuple

                    // broken chain

                    am_I_closest = (n == myself);
                    has_to_increment = am_I_closest || get<0>(n);

                    if(has_to_increment){
                        if( ! am_I_closest) { get<1>(n) += 1; } // can increment the hops count
                        get<2>(n) += distance_metric(node, get<3>(n));
                    }

                    if( get<2>(n) >= threshold_TTL_getter(node, myself) ){
                        // decayed 
                        return make_tuple(false, inf_int, error_ttl , node.uid
                        );
                    }

                    // if the "previous" is an extremity, then NO increment (to TTL) has to be performed
                    // else, if the "closest to an extremity" says that the increment should be performed, then I'll propagate it
                    get<0>(n) = (get<1>(n) > 0) && get<0>(n);

                    return n;
                }
            );

            return get<2>(data) > error_ttl;
        }

        template<typename D = int> FUN_EXPORT is_alive_decaying_t = export_list< decaying_node_data<D> >;
        

        template<typename node_t> int metric_unitary_hop(node_t& node){
            return 1;
        }

        template<typename node_t> int threshold_TTL_const_ten(node_t& node, decaying_node_data<int> node_data){
            return 10;
        }


        bool is_source_node(device_t id){
            return id % 17 == 0;
        }


        //! @brief Main function.
        MAIN()
        {
            bool in_chan, is_source;
            
            is_source = is_source_node(node.uid);

            in_chan = is_alive_decaying(CALL,
                (bool)is_source,
                true,
                (int) inf_int,
                [&](node_t& n, device_t id) -> int { return 1; }, // metric_unitary_hop,
                [&](node_t& n, decaying_node_data<int> data) -> int { return 10; } // threshold_TTL_const_ten
            );

            
            node.storage(tags::node_shape{}) = shape::sphere;
            node.storage(tags::in_channel{}) = in_chan;
            node.storage(tags::size{}) = 5;
            node.storage(tags::node_color{}) = color(is_source ? BLUE_VIOLET : GREEN);
        }

        //! @brief Export types used by the main function (update it when expanding the program).
        FUN_EXPORT main_t = export_list<
            is_alive_decaying_t<int>
        >;


    }  // namespace coordination


    /*
    namespace option
    {
        //! @brief Import tags to be used for component options.
        using namespace component::tags;

        //! @brief Import tags used by aggregate functions.
        using namespace coordination::tags;

        using store_t = tuple_store<
            node_color, color,
            size, double,
            node_shape, shape,
            in_channel, bool,
            id, device
            //
            >;
    }
    */

}  // namespace fcpp

#endif