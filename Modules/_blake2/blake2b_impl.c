/*
 * Written in 2013 by Dmitry Chestnykh <dmitry@codingrobots.com>
 * Modified for CPython by Christian Heimes <christian@python.org>
 *
 * To the extent possible under law, the author have dedicated all
 * copyright and related and neighboring rights to this software to
 * the public domain worldwide. This software is distributed without
 * any warranty. http://creativecommons.org/publicdomain/zero/1.0/
 */

/* WARNING: autogenerated file!
 *
 * The blake2s_impl.c is autogenerated from blake2b_impl.c.
 */

#include "Python.h"
#include "pystrhex.h"
#ifdef WITH_THREAD
#include "pythread.h"
#endif

#include "../hashlib.h"
#include "blake2ns.h"

#define HAVE_BLAKE2B 1
#define BLAKE2_LOCAL_INLINE(type) Py_LOCAL_INLINE(type)

#include "impl/blake2.h"
#include "impl/blake2-impl.h" /* for secure_zero_memory() and store48() */

#ifdef BLAKE2_USE_SSE
#include "impl/blake2b.c"
#else
#include "impl/blake2b-ref.c"
#endif


extern PyTypeObject PyBlake2_BLAKE2bType;

typedef struct {
    PyObject_HEAD
    blake2b_param    param;
    blake2b_state    state;
#ifdef WITH_THREAD
    PyThread_type_lock lock;
#endif
} BLAKE2bObject;

#include "clinic/blake2b_impl.c.h"

/*[clinic input]
module _blake2b
class _blake2b.blake2b "BLAKE2bObject *" "&PyBlake2_BLAKE2bType"
[clinic start generated code]*/
/*[clinic end generated code: output=da39a3ee5e6b4b0d input=6893358c6622aecf]*/


static BLAKE2bObject *
new_BLAKE2bObject(PyTypeObject *type)
{
    BLAKE2bObject *self;
    self = (BLAKE2bObject *)type->tp_alloc(type, 0);
#ifdef WITH_THREAD
    if (self != NULL) {
        self->lock = NULL;
    }
#endif
    return self;
}

/*[clinic input]
@classmethod
_blake2b.blake2b.__new__ as py_blake2b_new
    string as data: object = NULL
    *
    digest_size: int(c_default="BLAKE2B_OUTBYTES") = _blake2b.blake2b.MAX_DIGEST_SIZE
    key: Py_buffer = None
    salt: Py_buffer = None
    person: Py_buffer = None
    fanout: int = 1
    depth: int = 1
    leaf_size as leaf_size_obj: object = NULL
    node_offset as node_offset_obj: object = NULL
    node_depth: int = 0
    inner_size: int = 0
    last_node: bool = False

Return a new BLAKE2b hash object.
[clinic start generated code]*/

static PyObject *
py_blake2b_new_impl(PyTypeObject *type, PyObject *data, int digest_size,
                    Py_buffer *key, Py_buffer *salt, Py_buffer *person,
                    int fanout, int depth, PyObject *leaf_size_obj,
                    PyObject *node_offset_obj, int node_depth,
                    int inner_size, int last_node)
/*[clinic end generated code: output=7506d8d890e5f13b input=e41548dfa0866031]*/
{
    BLAKE2bObject *self = NULL;
    Py_buffer buf;

    unsigned long leaf_size = 0;
    unsigned long long node_offset = 0;

    self = new_BLAKE2bObject(type);
    if (self == NULL) {
        goto error;
    }

    /* Zero parameter block. */
    memset(&self->param, 0, sizeof(self->param));

    /* Set digest size. */
    if (digest_size <= 0 || digest_size > BLAKE2B_OUTBYTES) {
        PyErr_Format(PyExc_ValueError,
                "digest_size must be between 1 and %d bytes",
                BLAKE2B_OUTBYTES);
        goto error;
    }
    self->param.digest_length = digest_size;

    /* Set salt parameter. */
    if ((salt->obj != NULL) && salt->len) {
        if (salt->len > BLAKE2B_SALTBYTES) {
            PyErr_Format(PyExc_ValueError,
                "maximum salt length is %d bytes",
                BLAKE2B_SALTBYTES);
            goto error;
        }
        memcpy(self->param.salt, salt->buf, salt->len);
    }

    /* Set personalization parameter. */
    if ((person->obj != NULL) && person->len) {
        if (person->len > BLAKE2B_PERSONALBYTES) {
            PyErr_Format(PyExc_ValueError,
                "maximum person length is %d bytes",
                BLAKE2B_PERSONALBYTES);
            goto error;
        }
        memcpy(self->param.personal, person->buf, person->len);
    }

    /* Set tree parameters. */
    if (fanout < 0 || fanout > 255) {
        PyErr_SetString(PyExc_ValueError,
                "fanout must be between 0 and 255");
        goto error;
    }
    self->param.fanout = (uint8_t)fanout;

    if (depth <= 0 || depth > 255) {
        PyErr_SetString(PyExc_ValueError,
                "depth must be between 1 and 255");
        goto error;
    }
    self->param.depth = (uint8_t)depth;

    if (leaf_size_obj != NULL) {
        leaf_size = PyLong_AsUnsignedLong(leaf_size_obj);
        if (leaf_size == (unsigned long) -1 && PyErr_Occurred()) {
            goto error;
        }
        if (leaf_size > 0xFFFFFFFFU) {
            PyErr_SetString(PyExc_OverflowError, "leaf_size is too large");
            goto error;
        }
    }
    // NB: Simple assignment here would be incorrect on big endian platforms.
    store32(&(self->param.leaf_length), leaf_size);

    if (node_offset_obj != NULL) {
        node_offset = PyLong_AsUnsignedLongLong(node_offset_obj);
        if (node_offset == (unsigned long long) -1 && PyErr_Occurred()) {
            goto error;
        }
    }
#ifdef HAVE_BLAKE2S
    if (node_offset > 0xFFFFFFFFFFFFULL) {
        /* maximum 2**48 - 1 */
         PyErr_SetString(PyExc_OverflowError, "node_offset is too large");
         goto error;
     }
    store48(&(self->param.node_offset), node_offset);
#else
    // NB: Simple assignment here would be incorrect on big endian platforms.
    store64(&(self->param.node_offset), node_offset);
#endif

    if (node_depth < 0 || node_depth > 255) {
        PyErr_SetString(PyExc_ValueError,
                "node_depth must be between 0 and 255");
        goto error;
    }
    self->param.node_depth = node_depth;

    if (inner_size < 0 || inner_size > BLAKE2B_OUTBYTES) {
        PyErr_Format(PyExc_ValueError,
                "inner_size must be between 0 and is %d",
                BLAKE2B_OUTBYTES);
        goto error;
    }
    self->param.inner_length = inner_size;

    /* Set key length. */
    if ((key->obj != NULL) && key->len) {
        if (key->len > BLAKE2B_KEYBYTES) {
            PyErr_Format(PyExc_ValueError,
                "maximum key length is %d bytes",
                BLAKE2B_KEYBYTES);
            goto error;
        }
        self->param.key_length = (uint8_t)key->len;
    }

    /* Initialize hash state. */
    if (blake2b_init_param(&self->state, &self->param) < 0) {
        PyErr_SetString(PyExc_RuntimeError,
                "error initializing hash state");
        goto error;
    }

    /* Set last node flag (must come after initialization). */
    self->state.last_node = last_node;

    /* Process key block if any. */
    if (self->param.key_length) {
        uint8_t block[BLAKE2B_BLOCKBYTES];
        memset(block, 0, sizeof(block));
        memcpy(block, key->buf, key->len);
        blake2b_update(&self->state, block, sizeof(block));
        secure_zero_memory(block, sizeof(block));
    }

    /* Process initial data if any. */
    if (data != NULL) {
        GET_BUFFER_VIEW_OR_ERROR(data, &buf, goto error);

        if (buf.len >= HASHLIB_GIL_MINSIZE) {
            Py_BEGIN_ALLOW_THREADS
            blake2b_update(&self->state, buf.buf, buf.len);
            Py_END_ALLOW_THREADS
        } else {
            blake2b_update(&self->state, buf.buf, buf.len);
        }
        PyBuffer_Release(&buf);
    }

    return (PyObject *)self;

  error:
    if (self != NULL) {
        Py_DECREF(self);
    }
    return NULL;
}

/*[clinic input]
_blake2b.blake2b.copy

Return a copy of the hash object.
[clinic start generated code]*/

static PyObject *
_blake2b_blake2b_copy_impl(BLAKE2bObject *self)
/*[clinic end generated code: output=c89cd33550ab1543 input=4c9c319f18f10747]*/
{
    BLAKE2bObject *cpy;

    if ((cpy = new_BLAKE2bObject(Py_TYPE(self))) == NULL)
        return NULL;

    ENTER_HASHLIB(self);
    cpy->param = self->param;
    cpy->state = self->state;
    LEAVE_HASHLIB(self);
    return (PyObject *)cpy;
}

/*[clinic input]
_blake2b.blake2b.update

    obj: object
    /

Update this hash object's state with the provided string.
[clinic start generated code]*/

static PyObject *
_blake2b_blake2b_update(BLAKE2bObject *self, PyObject *obj)
/*[clinic end generated code: output=a888f07c4cddbe94 input=3ecb8c13ee4260f2]*/
{
    Py_buffer buf;

    GET_BUFFER_VIEW_OR_ERROUT(obj, &buf);

#ifdef WITH_THREAD
    if (self->lock == NULL && buf.len >= HASHLIB_GIL_MINSIZE)
        self->lock = PyThread_allocate_lock();

    if (self->lock != NULL) {
       Py_BEGIN_ALLOW_THREADS
       PyThread_acquire_lock(self->lock, 1);
       blake2b_update(&self->state, buf.buf, buf.len);
       PyThread_release_lock(self->lock);
       Py_END_ALLOW_THREADS
    } else {
        blake2b_update(&self->state, buf.buf, buf.len);
    }
#else
    blake2b_update(&self->state, buf.buf, buf.len);
#endif /* !WITH_THREAD */
    PyBuffer_Release(&buf);

    Py_RETURN_NONE;
}

/*[clinic input]
_blake2b.blake2b.digest

Return the digest value as a string of binary data.
[clinic start generated code]*/

static PyObject *
_blake2b_blake2b_digest_impl(BLAKE2bObject *self)
/*[clinic end generated code: output=b13a79360d984740 input=ac2fa462ebb1b9c7]*/
{
    uint8_t digest[BLAKE2B_OUTBYTES];
    blake2b_state state_cpy;

    ENTER_HASHLIB(self);
    state_cpy = self->state;
    blake2b_final(&state_cpy, digest, self->param.digest_length);
    LEAVE_HASHLIB(self);
    return PyBytes_FromStringAndSize((const char *)digest,
            self->param.digest_length);
}

/*[clinic input]
_blake2b.blake2b.hexdigest

Return the digest value as a string of hexadecimal digits.
[clinic start generated code]*/

static PyObject *
_blake2b_blake2b_hexdigest_impl(BLAKE2bObject *self)
/*[clinic end generated code: output=6a503611715b24bd input=d58f0b2f37812e33]*/
{
    uint8_t digest[BLAKE2B_OUTBYTES];
    blake2b_state state_cpy;

    ENTER_HASHLIB(self);
    state_cpy = self->state;
    blake2b_final(&state_cpy, digest, self->param.digest_length);
    LEAVE_HASHLIB(self);
    return _Py_strhex((const char *)digest, self->param.digest_length);
}


static PyMethodDef py_blake2b_methods[] = {
    _BLAKE2B_BLAKE2B_COPY_METHODDEF
    _BLAKE2B_BLAKE2B_DIGEST_METHODDEF
    _BLAKE2B_BLAKE2B_HEXDIGEST_METHODDEF
    _BLAKE2B_BLAKE2B_UPDATE_METHODDEF
    {NULL, NULL}
};



static PyObject *
py_blake2b_get_name(BLAKE2bObject *self, void *closure)
{
    return PyUnicode_FromString("blake2b");
}



static PyObject *
py_blake2b_get_block_size(BLAKE2bObject *self, void *closure)
{
    return PyLong_FromLong(BLAKE2B_BLOCKBYTES);
}



static PyObject *
py_blake2b_get_digest_size(BLAKE2bObject *self, void *closure)
{
    return PyLong_FromLong(self->param.digest_length);
}


static PyGetSetDef py_blake2b_getsetters[] = {
    {"name", (getter)py_blake2b_get_name,
        NULL, NULL, NULL},
    {"block_size", (getter)py_blake2b_get_block_size,
        NULL, NULL, NULL},
    {"digest_size", (getter)py_blake2b_get_digest_size,
        NULL, NULL, NULL},
    {NULL}
};


static void
py_blake2b_dealloc(PyObject *self)
{
    BLAKE2bObject *obj = (BLAKE2bObject *)self;

    /* Try not to leave state in memory. */
    secure_zero_memory(&obj->param, sizeof(obj->param));
    secure_zero_memory(&obj->state, sizeof(obj->state));
#ifdef WITH_THREAD
    if (obj->lock) {
        PyThread_free_lock(obj->lock);
        obj->lock = NULL;
    }
#endif
    PyObject_Del(self);
}


PyTypeObject PyBlake2_BLAKE2bType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_blake2.blake2b",        /* tp_name            */
    sizeof(BLAKE2bObject),    /* tp_size            */
    0,                        /* tp_itemsize        */
    py_blake2b_dealloc,       /* tp_dealloc         */
    0,                        /* tp_print           */
    0,                        /* tp_getattr         */
    0,                        /* tp_setattr         */
    0,                        /* tp_compare         */
    0,                        /* tp_repr            */
    0,                        /* tp_as_number       */
    0,                        /* tp_as_sequence     */
    0,                        /* tp_as_mapping      */
    0,                        /* tp_hash            */
    0,                        /* tp_call            */
    0,                        /* tp_str             */
    0,                        /* tp_getattro        */
    0,                        /* tp_setattro        */
    0,                        /* tp_as_buffer       */
    Py_TPFLAGS_DEFAULT,       /* tp_flags           */
    py_blake2b_new__doc__,    /* tp_doc             */
    0,                        /* tp_traverse        */
    0,                        /* tp_clear           */
    0,                        /* tp_richcompare     */
    0,                        /* tp_weaklistoffset  */
    0,                        /* tp_iter            */
    0,                        /* tp_iternext        */
    py_blake2b_methods,       /* tp_methods         */
    0,                        /* tp_members         */
    py_blake2b_getsetters,    /* tp_getset          */
    0,                        /* tp_base            */
    0,                        /* tp_dict            */
    0,                        /* tp_descr_get       */
    0,                        /* tp_descr_set       */
    0,                        /* tp_dictoffset      */
    0,                        /* tp_init            */
    0,                        /* tp_alloc           */
    py_blake2b_new,           /* tp_new             */
};
