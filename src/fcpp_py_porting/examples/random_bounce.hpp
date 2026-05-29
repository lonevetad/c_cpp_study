
//! Importing the FCPP library.
#include "lib/fcpp.hpp"

/**
 * @brief Namespace containing all the objects in the FCPP library.
 */
namespace fcpp {

    namespace coordination {
    
        namespace tags {
            /*
            for debugging the bouncing
            */
            struct node_bounce_side {};
            struct node_bounce_x {};
            struct node_bounce_y {};
        }

        //

        enum Side {
            TOP = 0,
            RIGHT,
            BOTTOM,
            LEFT
        };

        FUN int new_random_side(ARGS, Side current_side){
            int s = static_cast<int>(current_side);
            int next_side = 0;
            do {
                next_side = node.next_int(3);
            } while(next_side == s);
            return next_side;
        }

        using side_and_point_t = tuple<int, vec<option::dim>>; // side, x, y

        //! @brief return a side_and_point_t, with the current side and a random point lined up on that side
        FUN side_and_point_t random_point_on_side(
                ARGS,
                int current_side_int,
                const int& max_width,
                const int& max_height
            ){
            Side current_side = static_cast<Side>(current_side_int);
            switch(current_side){
                case(Side::TOP): {
                    return make_tuple(
                        current_side_int,
                        vec<option::dim>{static_cast<real_t>(node.next_int(max_width)), 0.0}
                    );
                }
                case(Side::RIGHT): {
                    return make_tuple(
                        current_side_int,
                        vec<option::dim>{static_cast<real_t>(max_width), static_cast<real_t>(node.next_int(max_height))}
                    );
                }
                case(Side::BOTTOM): {
                    return make_tuple(
                        current_side_int,
                        vec<option::dim>{static_cast<real_t>(node.next_int(max_width)), static_cast<real_t>(max_height)}
                    );
                }
                case(Side::LEFT): {
                    return make_tuple(
                        current_side_int,
                        vec<option::dim>{0.0, static_cast<real_t>(node.next_int(max_height))}
                    );
                }
            }
            std::cout << "what side is this? " << current_side_int << std::endl;
            throw std::runtime_error("Unkown side");
        }

                
        /**
        !@brief randomly moves the nodes every K turns
        */
        FUN side_and_point_t random_bounce(ARGS) { CODE
            return old(CALL,
                //std::move(
                    random_point_on_side( // starting destination
                        CALL,
                        node.next_int(3),
                        option::network_width,
                        option::network_height
                //    )
                ),
                [&](side_and_point_t const& current_side_destination) {
                    // approach the target, then change direction if needed
                    real_t dist = follow_target(CALL,
                        get<1>(current_side_destination),
                        static_cast<real_t>(option::maximum_movement_step),
                        static_cast<real_t>(option::period_between_bounces)
                    );
                    bool bounced = dist <= option::maximum_movement_step;
                    return bounced ?
                        random_point_on_side( // new destination
                            CALL,
                            static_cast<Side>(new_random_side(
                                CALL,
                                static_cast<Side>(get<0>(current_side_destination))
                            )),
                            option::network_width,
                            option::network_height
                        )
                        : current_side_destination
                    ;
                }
            );
        }
        FUN_EXPORT random_bounce_t = export_list<side_and_point_t>;

 
        /*
        FUN std::unique_ptr<side_and_point_t> random_point_on_side(
                ARGS,
                Side current_side,
                int max_width,
                int max_height
            ){
            int current_side_int = static_cast<int>(current_side);
            switch(current_side){
                case(Side::TOP): {
                    return std::make_unique<side_and_point_t>(
                        make_tuple(
                            current_side_int,
                            vec<option::dim>(node.next_int(max_width), 0)
                        )
                    );
                }
                case(Side::RIGHT): {
                    return std::make_unique<side_and_point_t>(
                        make_tuple(
                            current_side_int,
                            vec<option::dim>(max_width, node.next_int(max_height))
                        )
                    );
                }
                case(Side::BOTTOM): {
                    return std::make_unique<side_and_point_t>(
                        make_tuple(
                            current_side_int,
                            vec<option::dim>(node.next_int(max_width), max_height)
                        )
                    );
                }
                case(Side::LEFT): {
                    return std::make_unique<side_and_point_t>(
                        make_tuple(
                            current_side_int,
                            vec<option::dim>(0, node.next_int(max_height))
                        )
                    );
                }
            }
        }


        FUN std::unique_ptr<side_and_point_t> random_bounce(ARGS) { CODE
            return old(CALL,
                std::move(
                    random_point_on_side( // starting destination
                        CALL,
                        node.next_int(3),
                        option::network_width,
                        option::network_height
                    )
                ),
                [&](std::unique_ptr<side_and_point_t> current_side_destination) {
                    // approach the target, then change direction if needed
                    real_t dist = follow_target(CALL, get<1>(current_side_destination), option::period_between_bounces);
                    bool bounced = dist <= option::maximum_movement_step;
                    return bounced ?
                        random_point_on_side( // new destination
                            CALL,
                            new_random_side(
                                CALL,
                                static_cast<Side>(get<0>(current_side_destination))
                            ),
                            option::network_width,
                            option::network_height
                        )
                        : std::move(current_side_destination)
                    ;
                }
            );
        }
        FUN_EXPORT random_bounce_t = export_list<std::unique_ptr<side_and_point_t>>;

        */

    } // namespace coordination

} // namespace fcpp