/* Frozen python modules */

#ifndef Py_FROZENMODULES_H
#define Py_FROZENMODULES_H
#ifdef __cplusplus
extern "C" {
#endif


PyAPI_FUNC(void) _PyFrozenModules_Init(void);
PyAPI_FUNC(PyObject*) PyFrozenModule_Lookup(PyObject* name);
PyAPI_FUNC(void) _PyFrozenModules_Finalize(void);

#ifdef __cplusplus
}
#endif
#endif /* !Py_FROZENMODULES_H */
