#ifndef Py_INTERNAL_GLOBALCACHE_H
#define Py_INTERNAL_GLOBALCACHE_H
#ifdef __cplusplus
extern "C" {
#endif

PyObject *
_PyCode_LoadGlobalCached(PyCodeObject *code, PyDictObject *globals, PyDictObject *builtins, int offset);

#ifdef __cplusplus
}
#endif
#endif /* !Py_INTERNAL_GLOBALCACHE_H */

