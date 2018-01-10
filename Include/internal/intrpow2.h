#ifndef Py_INTERNAL_INTRPOW2_H
#define Py_INTERNAL_INTRPOW2_H

#ifdef __GNUC__
#define INTRINSIC_NEAREST_POWER_OF_TWO(X)                                    \
    __builtin_choose_expr (                                                  \
        __builtin_types_compatible_p (Py_ssize_t, int),                      \
            ((Py_ssize_t) (1 << ((unsigned)                                  \
                                 ((8 * sizeof (Py_ssize_t)) -                \
                                   __builtin_clz(X))))),                     \
            __builtin_choose_expr (                                          \
                __builtin_types_compatible_p (Py_ssize_t, long),             \
                    ((Py_ssize_t) (1 << ((unsigned)                          \
                                         ((8 * sizeof (Py_ssize_t)) -        \
                                           __builtin_clzl(X))))),            \
                __builtin_choose_expr (                                      \
                    __builtin_types_compatible_p (Py_ssize_t, long long),    \
                        ((Py_ssize_t) (1 << ((unsigned)                      \
                                             ((8 * sizeof (Py_ssize_t)) -    \
                                               __builtin_clzll(X))))), -1)))
#endif

#endif /* !Py_INTERNAL_INTRPOW2_H */
