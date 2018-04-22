/* Chilled python modules */

#ifndef Py_CHILLEDMODULES_H
#define Py_CHILLEDMODULES_H
#ifdef __cplusplus
extern "C" {
#endif


extern void _PyChilledModules_Init(void);
extern PyObject* _PyChilledModule_Lookup(PyObject* name);
extern void _PyChilledModules_Finalize(void);
extern int _PyChilledModules_ImportBootstrap(void);

#ifdef __cplusplus
}
#endif
#endif /* !Py_CHILLEDMODULES_H */
