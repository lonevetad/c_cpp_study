
//! Importing the FCPP library.
#include "lib/fcpp.hpp"
#include "run/shared.hpp"

/**
 * @brief Namespace containing all the objects in the FCPP library.
 */
namespace fcpp {

    static device_t gcd (device_t a, device_t b) {
        device_t r, i;
        if(a <= 0 || b <= 0){
            return 1;
        }
        while(b != 0){
            r = a % b;
            a = b;
            b = r;
        }
        return a;
    }
    static bool is_coprime(device_t a, device_t b){
        return gcd(a, b) == 1;
    }

    //! @brief Dummy function to create a dummy "sharded database": a vector
    using vector_coprime_IDs_t = std::vector<device_t>;
    FUN vector_coprime_IDs_t new_vector_coprime_IDs(ARGS) { CODE
        vector_coprime_IDs_t result;
        common::unit c{};
        for_each_nbr(CALL, [&](device_t nbr_id) {
            if (is_coprime(nbr_id, node.uid))
                result.push_back(nbr_id);
            return c;
        });
        return result;
    }
    FUN_EXPORT new_vector_coprime_IDs_t = export_list<device_t, for_each_nbr_t>;



    template <
        typename node_t,
        typename G,
#if __cplusplus <= 201402L
        typename T = typename std::result_of<G(node_t&)>::type,
#else
        typename T = std::invoke_result_t<G, node_t&>,
#endif
        typename = common::if_signature<G, T(node_t&)>
    >
    std::map<device_t, T> new_coprime_nbr_data(node_t& node, trace_t call_point, G value_fn)
    {
        std::map<device_t, T> result;
        for_each_nbr(node, call_point, [&](device_t nbr_id) -> common::unit {
            if (is_coprime(nbr_id, node.uid))
                result.emplace(nbr_id, value_fn(node));
            return {};
        });
        return result;
    }
    FUN_EXPORT new_coprime_nbr_data_t = export_list<for_each_nbr_t>;
}
