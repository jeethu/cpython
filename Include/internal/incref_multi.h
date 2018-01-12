#ifndef Py_INTERNAL_INCREFMULTI_H
#define Py_INTERNAL_INCREFMULTI_H

#ifdef Py_REF_DEBUG
#define _Py_INC_REFTOTAL_MULTI(n)        _Py_RefTotal += n
#else
#define _Py_INC_REFTOTAL_MULTI(n)
#endif

#define Py_INCREF_MULTI(op, n)                  \
    do {                                        \
        _Py_INC_REFTOTAL_MULTI(n);              \
        ((PyObject *)(op))->ob_refcnt += n;     \
    } while (0)

#endif /* !Py_INTERNAL_CEVAL_H */

