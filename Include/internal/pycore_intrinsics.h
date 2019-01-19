#ifndef Py_INTERNAL_INTRINSICS_H
#define Py_INTERNAL_INTRINSICS_H

#ifdef __GNUC__
#define _INTRINSIC_NEAREST_POWER_OF_TWO(T, X)                                \
    __builtin_choose_expr(                                                   \
        __builtin_types_compatible_p(T, int),                                \
            ((T)(1 << ((unsigned)                                            \
                                 ((8 * sizeof (T)) -                         \
                                   __builtin_clz(X))))),                     \
            __builtin_choose_expr(                                           \
                __builtin_types_compatible_p(T, long),                       \
                    ((T)(1 << ((unsigned)                                    \
                                         ((8 * sizeof (T)) -                 \
                                           __builtin_clzl(X))))),            \
                __builtin_choose_expr(                                       \
                    __builtin_types_compatible_p(T, long long),              \
                        ((T)(1 << ((unsigned)                                \
                                             ((8 * sizeof (T)) -             \
                                               __builtin_clzll(X))))), -1)))

#define INTRINSIC_NEAREST_POWER_OF_TWO(x, m) (x < m ?                        \
            m : (((x & (x - 1)) == 0) ?                                      \
                 x : _INTRINSIC_NEAREST_POWER_OF_TWO(Py_ssize_t, x)))
#endif

#endif /* !Py_INTERNAL_INTRPOW2_H */
