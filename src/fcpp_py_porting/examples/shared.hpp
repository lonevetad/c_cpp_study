
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

}
