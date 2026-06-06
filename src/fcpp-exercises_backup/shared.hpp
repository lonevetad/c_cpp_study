#ifndef SHARED_EXERCISES__
#define SHARED_EXERCISES__

#include <map>

//! Importing the FCPP library.
#include "lib/fcpp.hpp"

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

    template <typename node_t, typename F, typename = common::if_signature<F, common::unit(device_t)>>
    common::unit for_each_nbr(node_t& node, trace_t call_point, F&& nbr_consumer) {
        return coordination::fold_hood(node, call_point,
            [&](device_t nbr_id, common::unit, common::unit) -> common::unit {
                nbr_consumer(nbr_id);
                return {};
            },
            common::unit{}, common::unit{});
    }
    FUN_EXPORT for_each_nbr_t = export_list<device_t, common::unit>; // even F?




    // Builds a field<V> from a map whose keys are device UIDs.
    // `default_val` is used for every device NOT present in the map.
    template <typename V>
    field<V> map_keys_to_field(V default_val, std::map<device_t, V> const& m) {
        std::vector<device_t> ids;
        std::vector<V> vals;
        ids.reserve(m.size());
        vals.reserve(m.size() + 1);
        vals.push_back(default_val);           // index 0: default
#if __cplusplus <= 201402L
        // C++14 and older
        for (auto const& kv : m) {       // std::map iterates in key order
            device_t uid = kv.first;
            V v = kv.second;
#else
        // C++17 and earlier
        for (auto const& [uid, v] : m) {       // std::map iterates in key order
#endif
            ids.push_back(uid);
            vals.push_back(v);
        }
        return details::make_field(std::move(ids), std::move(vals));
    }

    // Builds a field<V> from a map whose keys are somethings that
    // might be converted into a device UIDs through a provided function
    // (which might just be a getter or a tuple-extractor).
    // `default_val` is used for every device NOT present in the map.
    template <typename V, typename K, typename KE, typename = common::if_signature<KE, device_t(K)>>
    field<V> map_keys_to_field(V default_val, std::map<K, V> const& m, KE&& uid_extractor) {
        std::vector<device_t> ids;
        std::vector<V> vals;
        ids.reserve(m.size());
        vals.reserve(m.size() + 1);
        vals.push_back(default_val);           // index 0: default
#if __cplusplus <= 201402L
        // C++14 and older
        for (auto const& kv : m) {       // std::map iterates in key order
            K k = kv.first;
            V v = kv.second;
#else
        // C++17 and earlier
        for (auto const& [k, v] : m) {       // std::map iterates in key order
#endif
            ids.push_back(uid_extractor(k));
            vals.push_back(v);
        }
        return details::make_field(std::move(ids), std::move(vals));
    }
}

#endif