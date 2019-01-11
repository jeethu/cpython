import unittest, test.support
from test.support.script_helper import assert_python_ok, assert_python_failure
import sys, io, os
import struct
import subprocess
import textwrap
import warnings
import operator
import codecs
import gc
import sysconfig
import locale

# count the number of test runs, used to create unique
# strings to intern in test_intern()
numruns = 0


class SysModuleTest(unittest.TestCase):

    def setUp(self):
        self.orig_stdout = sys.stdout
        self.orig_stderr = sys.stderr
        self.orig_displayhook = sys.displayhook

    def tearDown(self):
        sys.stdout = self.orig_stdout
        sys.stderr = self.orig_stderr
        sys.displayhook = self.orig_displayhook
        test.support.reap_children()

    def test_original_displayhook(self):
        import builtins
        out = io.StringIO()
        sys.stdout = out

        dh = sys.__displayhook__

        self.assertRaises(TypeError, dh)
        if hasattr(builtins, "_"):
            del builtins._

        dh(None)
        self.assertEqual(out.getvalue(), "")
        self.assertTrue(not hasattr(builtins, "_"))
        dh(42)
        self.assertEqual(out.getvalue(), "42\n")
        self.assertEqual(builtins._, 42)

        del sys.stdout
        self.assertRaises(RuntimeError, dh, 42)

    def test_lost_displayhook(self):
        del sys.displayhook
        code = compile("42", "<string>", "single")
        self.assertRaises(RuntimeError, eval, code)

    def test_custom_displayhook(self):
        def baddisplayhook(obj):
            raise ValueError
        sys.displayhook = baddisplayhook
        code = compile("42", "<string>", "single")
        self.assertRaises(ValueError, eval, code)

    def test_original_excepthook(self):
        err = io.StringIO()
        sys.stderr = err

        eh = sys.__excepthook__

        self.assertRaises(TypeError, eh)
        try:
            raise ValueError(42)
        except ValueError as exc:
            eh(*sys.exc_info())

        self.assertTrue(err.getvalue().endswith("ValueError: 42\n"))

    def test_excepthook(self):
        with test.support.captured_output("stderr") as stderr:
            sys.excepthook(1, '1', 1)
        self.assertTrue("TypeError: print_exception(): Exception expected for " \
                         "value, str found" in stderr.getvalue())

    # FIXME: testing the code for a lost or replaced excepthook in
    # Python/pythonrun.c::PyErr_PrintEx() is tricky.

    def test_exit(self):
        # call with two arguments
        self.assertRaises(TypeError, sys.exit, 42, 42)

        # call without argument
        with self.assertRaises(SystemExit) as cm:
            sys.exit()
        self.assertIsNone(cm.exception.code)

        rc, out, err = assert_python_ok('-c', 'import sys; sys.exit()')
        self.assertEqual(rc, 0)
        self.assertEqual(out, b'')
        self.assertEqual(err, b'')

        # call with integer argument
        with self.assertRaises(SystemExit) as cm:
            sys.exit(42)
        self.assertEqual(cm.exception.code, 42)

        # call with tuple argument with one entry
        # entry will be unpacked
        with self.assertRaises(SystemExit) as cm:
            sys.exit((42,))
        self.assertEqual(cm.exception.code, 42)

        # call with string argument
        with self.assertRaises(SystemExit) as cm:
            sys.exit("exit")
        self.assertEqual(cm.exception.code, "exit")

        # call with tuple argument with two entries
        with self.assertRaises(SystemExit) as cm:
            sys.exit((17, 23))
        self.assertEqual(cm.exception.code, (17, 23))

        # test that the exit machinery handles SystemExits properly
        rc, out, err = assert_python_failure('-c', 'raise SystemExit(47)')
        self.assertEqual(rc, 47)
        self.assertEqual(out, b'')
        self.assertEqual(err, b'')

        def check_exit_message(code, expected, **env_vars):
            rc, out, err = assert_python_failure('-c', code, **env_vars)
            self.assertEqual(rc, 1)
            self.assertEqual(out, b'')
            self.assertTrue(err.startswith(expected),
                "%s doesn't start with %s" % (ascii(err), ascii(expected)))

        # test that stderr buffer is flushed before the exit message is written
        # into stderr
        check_exit_message(
            r'import sys; sys.stderr.write("unflushed,"); sys.exit("message")',
            b"unflushed,message")

        # test that the exit message is written with backslashreplace error
        # handler to stderr
        check_exit_message(
            r'import sys; sys.exit("surrogates:\uDCFF")',
            b"surrogates:\\udcff")

        # test that the unicode message is encoded to the stderr encoding
        # instead of the default encoding (utf8)
        check_exit_message(
            r'import sys; sys.exit("h\xe9")',
            b"h\xe9", PYTHONIOENCODING='latin-1')

    def test_getdefaultencoding(self):
        self.assertRaises(TypeError, sys.getdefaultencoding, 42)
        # can't check more than the type, as the user might have changed it
        self.assertIsInstance(sys.getdefaultencoding(), str)

    # testing sys.settrace() is done in test_sys_settrace.py
    # testing sys.setprofile() is done in test_sys_setprofile.py

    def test_setcheckinterval(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.assertRaises(TypeError, sys.setcheckinterval)
            orig = sys.getcheckinterval()
            for n in 0, 100, 120, orig: # orig last to restore starting state
                sys.setcheckinterval(n)
                self.assertEqual(sys.getcheckinterval(), n)

    def test_switchinterval(self):
        self.assertRaises(TypeError, sys.setswitchinterval)
        self.assertRaises(TypeError, sys.setswitchinterval, "a")
        self.assertRaises(ValueError, sys.setswitchinterval, -1.0)
        self.assertRaises(ValueError, sys.setswitchinterval, 0.0)
        orig = sys.getswitchinterval()
        # sanity check
        self.assertTrue(orig < 0.5, orig)
        try:
            for n in 0.00001, 0.05, 3.0, orig:
                sys.setswitchinterval(n)
                self.assertAlmostEqual(sys.getswitchinterval(), n)
        finally:
            sys.setswitchinterval(orig)

    def test_recursionlimit(self):
        self.assertRaises(TypeError, sys.getrecursionlimit, 42)
        oldlimit = sys.getrecursionlimit()
        self.assertRaises(TypeError, sys.setrecursionlimit)
        self.assertRaises(ValueError, sys.setrecursionlimit, -42)
        sys.setrecursionlimit(10000)
        self.assertEqual(sys.getrecursionlimit(), 10000)
        sys.setrecursionlimit(oldlimit)

    def test_recursionlimit_recovery(self):
        if hasattr(sys, 'gettrace') and sys.gettrace():
            self.skipTest('fatal error if run with a trace function')

        oldlimit = sys.getrecursionlimit()
        def f():
            f()
        try:
            for depth in (10, 25, 50, 75, 100, 250, 1000):
                try:
                    sys.setrecursionlimit(depth)
                except RecursionError:
                    # Issue #25274: The recursion limit is too low at the
                    # current recursion depth
                    continue

                # Issue #5392: test stack overflow after hitting recursion
                # limit twice
                self.assertRaises(RecursionError, f)
                self.assertRaises(RecursionError, f)
        finally:
            sys.setrecursionlimit(oldlimit)

    @test.support.cpython_only
    def test_setrecursionlimit_recursion_depth(self):
        # Issue #25274: Setting a low recursion limit must be blocked if the
        # current recursion depth is already higher than the "lower-water
        # mark". Otherwise, it may not be possible anymore to
        # reset the overflowed flag to 0.

        from _testcapi import get_recursion_depth

        def set_recursion_limit_at_depth(depth, limit):
            recursion_depth = get_recursion_depth()
            if recursion_depth >= depth:
                with self.assertRaises(RecursionError) as cm:
                    sys.setrecursionlimit(limit)
                self.assertRegex(str(cm.exception),
                                 "cannot set the recursion limit to [0-9]+ "
                                 "at the recursion depth [0-9]+: "
                                 "the limit is too low")
            else:
                set_recursion_limit_at_depth(depth, limit)

        oldlimit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(1000)

            for limit in (10, 25, 50, 75, 100, 150, 200):
                # formula extracted from _Py_RecursionLimitLowerWaterMark()
                if limit > 200:
                    depth = limit - 50
                else:
                    depth = limit * 3 // 4
                set_recursion_limit_at_depth(depth, limit)
        finally:
            sys.setrecursionlimit(oldlimit)

    def test_recursionlimit_fatalerror(self):
        # A fatal error occurs if a second recursion limit is hit when recovering
        # from a first one.
        code = textwrap.dedent("""
            import sys

            def f():
                try:
                    f()
                except RecursionError:
                    f()

            sys.setrecursionlimit(%d)
            f()""")
        with test.support.SuppressCrashReport():
            for i in (50, 1000):
                sub = subprocess.Popen([sys.executable, '-c', code % i],
                    stderr=subprocess.PIPE)
                err = sub.communicate()[1]
                self.assertTrue(sub.returncode, sub.returncode)
                self.assertIn(
                    b"Fatal Python error: Cannot recover from stack overflow",
                    err)

    def test_getwindowsversion(self):
        # Raise SkipTest if sys doesn't have getwindowsversion attribute
        test.support.get_attribute(sys, "getwindowsversion")
        v = sys.getwindowsversion()
        self.assertEqual(len(v), 5)
        self.assertIsInstance(v[0], int)
        self.assertIsInstance(v[1], int)
        self.assertIsInstance(v[2], int)
        self.assertIsInstance(v[3], int)
        self.assertIsInstance(v[4], str)
        self.assertRaises(IndexError, operator.getitem, v, 5)
        self.assertIsInstance(v.major, int)
        self.assertIsInstance(v.minor, int)
        self.assertIsInstance(v.build, int)
        self.assertIsInstance(v.platform, int)
        self.assertIsInstance(v.service_pack, str)
        self.assertIsInstance(v.service_pack_minor, int)
        self.assertIsInstance(v.service_pack_major, int)
        self.assertIsInstance(v.suite_mask, int)
        self.assertIsInstance(v.product_type, int)
        self.assertEqual(v[0], v.major)
        self.assertEqual(v[1], v.minor)
        self.assertEqual(v[2], v.build)
        self.assertEqual(v[3], v.platform)
        self.assertEqual(v[4], v.service_pack)

        # This is how platform.py calls it. Make sure tuple
        #  still has 5 elements
        maj, min, buildno, plat, csd = sys.getwindowsversion()

    def test_call_tracing(self):
        self.assertRaises(TypeError, sys.call_tracing, type, 2)

    @unittest.skipUnless(hasattr(sys, "setdlopenflags"),
                         'test needs sys.setdlopenflags()')
    def test_dlopenflags(self):
        self.assertTrue(hasattr(sys, "getdlopenflags"))
        self.assertRaises(TypeError, sys.getdlopenflags, 42)
        oldflags = sys.getdlopenflags()
        self.assertRaises(TypeError, sys.setdlopenflags)
        sys.setdlopenflags(oldflags+1)
        self.assertEqual(sys.getdlopenflags(), oldflags+1)
        sys.setdlopenflags(oldflags)

    @test.support.refcount_test
    def test_refcount(self):
        # n here must be a global in order for this test to pass while
        # tracing with a python function.  Tracing calls PyFrame_FastToLocals
        # which will add a copy of any locals to the frame object, causing
        # the reference count to increase by 2 instead of 1.
        global n
        self.assertRaises(TypeError, sys.getrefcount)
        c = sys.getrefcount(None)
        n = None
        self.assertEqual(sys.getrefcount(None), c+1)
        del n
        self.assertEqual(sys.getrefcount(None), c)
        if hasattr(sys, "gettotalrefcount"):
            self.assertIsInstance(sys.gettotalrefcount(), int)

    def test_getframe(self):
        self.assertRaises(TypeError, sys._getframe, 42, 42)
        self.assertRaises(ValueError, sys._getframe, 2000000000)
        self.assertTrue(
            SysModuleTest.test_getframe.__code__ \
            is sys._getframe().f_code
        )

    # sys._current_frames() is a CPython-only gimmick.
    @test.support.reap_threads
    def test_current_frames(self):
        import threading
        import traceback

        # Spawn a thread that blocks at a known place.  Then the main
        # thread does sys._current_frames(), and verifies that the frames
        # returned make sense.
        entered_g = threading.Event()
        leave_g = threading.Event()
        thread_info = []  # the thread's id

        def f123():
            g456()

        def g456():
            thread_info.append(threading.get_ident())
            entered_g.set()
            leave_g.wait()

        t = threading.Thread(target=f123)
        t.start()
        entered_g.wait()

        # At this point, t has finished its entered_g.set(), although it's
        # impossible to guess whether it's still on that line or has moved on
        # to its leave_g.wait().
        self.assertEqual(len(thread_info), 1)
        thread_id = thread_info[0]

        d = sys._current_frames()
        for tid in d:
            self.assertIsInstance(tid, int)
            self.assertGreater(tid, 0)

        main_id = threading.get_ident()
        self.assertIn(main_id, d)
        self.assertIn(thread_id, d)

        # Verify that the captured main-thread frame is _this_ frame.
        frame = d.pop(main_id)
        self.assertTrue(frame is sys._getframe())

        # Verify that the captured thread frame is blocked in g456, called
        # from f123.  This is a litte tricky, since various bits of
        # threading.py are also in the thread's call stack.
        frame = d.pop(thread_id)
        stack = traceback.extract_stack(frame)
        for i, (filename, lineno, funcname, sourceline) in enumerate(stack):
            if funcname == "f123":
                break
        else:
            self.fail("didn't find f123() on thread's call stack")

        self.assertEqual(sourceline, "g456()")

        # And the next record must be for g456().
        filename, lineno, funcname, sourceline = stack[i+1]
        self.assertEqual(funcname, "g456")
        self.assertIn(sourceline, ["leave_g.wait()", "entered_g.set()"])

        # Reap the spawned thread.
        leave_g.set()
        t.join()

    def test_attributes(self):
        self.assertIsInstance(sys.api_version, int)
        self.assertIsInstance(sys.argv, list)
        self.assertIn(sys.byteorder, ("little", "big"))
        self.assertIsInstance(sys.builtin_module_names, tuple)
        self.assertIsInstance(sys.copyright, str)
        self.assertIsInstance(sys.exec_prefix, str)
        self.assertIsInstance(sys.base_exec_prefix, str)
        self.assertIsInstance(sys.executable, str)
        self.assertEqual(len(sys.float_info), 11)
        self.assertEqual(sys.float_info.radix, 2)
        self.assertEqual(len(sys.int_info), 2)
        self.assertTrue(sys.int_info.bits_per_digit % 5 == 0)
        self.assertTrue(sys.int_info.sizeof_digit >= 1)
        self.assertEqual(type(sys.int_info.bits_per_digit), int)
        self.assertEqual(type(sys.int_info.sizeof_digit), int)
        self.assertIsInstance(sys.hexversion, int)

        self.assertEqual(len(sys.hash_info), 9)
        self.assertLess(sys.hash_info.modulus, 2**sys.hash_info.width)
        # sys.hash_info.modulus should be a prime; we do a quick
        # probable primality test (doesn't exclude the possibility of
        # a Carmichael number)
        for x in range(1, 100):
            self.assertEqual(
                pow(x, sys.hash_info.modulus-1, sys.hash_info.modulus),
                1,
                "sys.hash_info.modulus {} is a non-prime".format(
                    sys.hash_info.modulus)
                )
        self.assertIsInstance(sys.hash_info.inf, int)
        self.assertIsInstance(sys.hash_info.nan, int)
        self.assertIsInstance(sys.hash_info.imag, int)
        algo = sysconfig.get_config_var("Py_HASH_ALGORITHM")
        if sys.hash_info.algorithm in {"fnv", "siphash24"}:
            self.assertIn(sys.hash_info.hash_bits, {32, 64})
            self.assertIn(sys.hash_info.seed_bits, {32, 64, 128})

            if algo == 1:
                self.assertEqual(sys.hash_info.algorithm, "siphash24")
            elif algo == 2:
                self.assertEqual(sys.hash_info.algorithm, "fnv")
            else:
                self.assertIn(sys.hash_info.algorithm, {"fnv", "siphash24"})
        else:
            # PY_HASH_EXTERNAL
            self.assertEqual(algo, 0)
        self.assertGreaterEqual(sys.hash_info.cutoff, 0)
        self.assertLess(sys.hash_info.cutoff, 8)

        self.assertIsInstance(sys.maxsize, int)
        self.assertIsInstance(sys.maxunicode, int)
        self.assertEqual(sys.maxunicode, 0x10FFFF)
        self.assertIsInstance(sys.platform, str)
        self.assertIsInstance(sys.prefix, str)
        self.assertIsInstance(sys.base_prefix, str)
        self.assertIsInstance(sys.version, str)
        vi = sys.version_info
        self.assertIsInstance(vi[:], tuple)
        self.assertEqual(len(vi), 5)
        self.assertIsInstance(vi[0], int)
        self.assertIsInstance(vi[1], int)
        self.assertIsInstance(vi[2], int)
        self.assertIn(vi[3], ("alpha", "beta", "candidate", "final"))
        self.assertIsInstance(vi[4], int)
        self.assertIsInstance(vi.major, int)
        self.assertIsInstance(vi.minor, int)
        self.assertIsInstance(vi.micro, int)
        self.assertIn(vi.releaselevel, ("alpha", "beta", "candidate", "final"))
        self.assertIsInstance(vi.serial, int)
        self.assertEqual(vi[0], vi.major)
        self.assertEqual(vi[1], vi.minor)
        self.assertEqual(vi[2], vi.micro)
        self.assertEqual(vi[3], vi.releaselevel)
        self.assertEqual(vi[4], vi.serial)
        self.assertTrue(vi > (1,0,0))
        self.assertIsInstance(sys.float_repr_style, str)
        self.assertIn(sys.float_repr_style, ('short', 'legacy'))
        if not sys.platform.startswith('win'):
            self.assertIsInstance(sys.abiflags, str)

    def test_thread_info(self):
        info = sys.thread_info
        self.assertEqual(len(info), 3)
        self.assertIn(info.name, ('nt', 'pthread', 'solaris', None))
        self.assertIn(info.lock, ('semaphore', 'mutex+cond', None))

    def test_43581(self):
        # Can't use sys.stdout, as this is a StringIO object when
        # the test runs under regrtest.
        self.assertEqual(sys.__stdout__.encoding, sys.__stderr__.encoding)

    def test_intern(self):
        global numruns
        numruns += 1
        self.assertRaises(TypeError, sys.intern)
        s = "never interned before" + str(numruns)
        self.assertTrue(sys.intern(s) is s)
        s2 = s.swapcase().swapcase()
        self.assertTrue(sys.intern(s2) is s)

        # Subclasses of string can't be interned, because they
        # provide too much opportunity for insane things to happen.
        # We don't want them in the interned dict and if they aren't
        # actually interned, we don't want to create the appearance
        # that they are by allowing intern() to succeed.
        class S(str):
            def __hash__(self):
                return 123

        self.assertRaises(TypeError, sys.intern, S("abc"))

    def test_sys_flags(self):
        self.assertTrue(sys.flags)
        attrs = ("debug",
                 "inspect", "interactive", "optimize", "dont_write_bytecode",
                 "no_user_site", "no_site", "ignore_environment", "verbose",
                 "bytes_warning", "quiet", "hash_randomization", "isolated",
                 "dev_mode", "utf8_mode")
        for attr in attrs:
            self.assertTrue(hasattr(sys.flags, attr), attr)
            attr_type = bool if attr == "dev_mode" else int
            self.assertEqual(type(getattr(sys.flags, attr)), attr_type, attr)
        self.assertTrue(repr(sys.flags))
        self.assertEqual(len(sys.flags), len(attrs))

        self.assertIn(sys.flags.utf8_mode, {0, 1, 2})

    def assert_raise_on_new_sys_type(self, sys_attr):
        # Users are intentionally prevented from creating new instances of
        # sys.flags, sys.version_info, and sys.getwindowsversion.
        attr_type = type(sys_attr)
        with self.assertRaises(TypeError):
            attr_type()
        with self.assertRaises(TypeError):
            attr_type.__new__(attr_type)

    def test_sys_flags_no_instantiation(self):
        self.assert_raise_on_new_sys_type(sys.flags)

    def test_sys_version_info_no_instantiation(self):
        self.assert_raise_on_new_sys_type(sys.version_info)

    def test_sys_getwindowsversion_no_instantiation(self):
        # Skip if not being run on Windows.
        test.support.get_attribute(sys, "getwindowsversion")
        self.assert_raise_on_new_sys_type(sys.getwindowsversion())

    @test.support.cpython_only
    def test_clear_type_cache(self):
        sys._clear_type_cache()

    def test_ioencoding(self):
        env = dict(os.environ)

        # Test character: cent sign, encoded as 0x4A (ASCII J) in CP424,
        # not representable in ASCII.

        env["PYTHONIOENCODING"] = "cp424"
        p = subprocess.Popen([sys.executable, "-c", 'print(chr(0xa2))'],
                             stdout = subprocess.PIPE, env=env)
        out = p.communicate()[0].strip()
        expected = ("\xa2" + os.linesep).encode("cp424")
        self.assertEqual(out, expected)

        env["PYTHONIOENCODING"] = "ascii:replace"
        p = subprocess.Popen([sys.executable, "-c", 'print(chr(0xa2))'],
                             stdout = subprocess.PIPE, env=env)
        out = p.communicate()[0].strip()
        self.assertEqual(out, b'?')

        env["PYTHONIOENCODING"] = "ascii"
        p = subprocess.Popen([sys.executable, "-c", 'print(chr(0xa2))'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env=env)
        out, err = p.communicate()
        self.assertEqual(out, b'')
        self.assertIn(b'UnicodeEncodeError:', err)
        self.assertIn(rb"'\xa2'", err)

        env["PYTHONIOENCODING"] = "ascii:"
        p = subprocess.Popen([sys.executable, "-c", 'print(chr(0xa2))'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env=env)
        out, err = p.communicate()
        self.assertEqual(out, b'')
        self.assertIn(b'UnicodeEncodeError:', err)
        self.assertIn(rb"'\xa2'", err)

        env["PYTHONIOENCODING"] = ":surrogateescape"
        p = subprocess.Popen([sys.executable, "-c", 'print(chr(0xdcbd))'],
                             stdout=subprocess.PIPE, env=env)
        out = p.communicate()[0].strip()
        self.assertEqual(out, b'\xbd')

    @unittest.skipUnless(test.support.FS_NONASCII,
                         'requires OS support of non-ASCII encodings')
    @unittest.skipUnless(sys.getfilesystemencoding() == locale.getpreferredencoding(False),
                         'requires FS encoding to match locale')
    def test_ioencoding_nonascii(self):
        env = dict(os.environ)

        env["PYTHONIOENCODING"] = ""
        p = subprocess.Popen([sys.executable, "-c",
                                'print(%a)' % test.support.FS_NONASCII],
                                stdout=subprocess.PIPE, env=env)
        out = p.communicate()[0].strip()
        self.assertEqual(out, os.fsencode(test.support.FS_NONASCII))

    @unittest.skipIf(sys.base_prefix != sys.prefix,
                     'Test is not venv-compatible')
    def test_executable(self):
        # sys.executable should be absolute
        self.assertEqual(os.path.abspath(sys.executable), sys.executable)

        # Issue #7774: Ensure that sys.executable is an empty string if argv[0]
        # has been set to a non existent program name and Python is unable to
        # retrieve the real program name

        # For a normal installation, it should work without 'cwd'
        # argument. For test runs in the build directory, see #7774.
        python_dir = os.path.dirname(os.path.realpath(sys.executable))
        p = subprocess.Popen(
            ["nonexistent", "-c",
             'import sys; print(sys.executable.encode("ascii", "backslashreplace"))'],
            executable=sys.executable, stdout=subprocess.PIPE, cwd=python_dir)
        stdout = p.communicate()[0]
        executable = stdout.strip().decode("ASCII")
        p.wait()
        self.assertIn(executable, ["b''", repr(sys.executable.encode("ascii", "backslashreplace"))])

    def check_fsencoding(self, fs_encoding, expected=None):
        self.assertIsNotNone(fs_encoding)
        codecs.lookup(fs_encoding)
        if expected:
            self.assertEqual(fs_encoding, expected)

    def test_getfilesystemencoding(self):
        fs_encoding = sys.getfilesystemencoding()
        if sys.platform == 'darwin':
            expected = 'utf-8'
        else:
            expected = None
        self.check_fsencoding(fs_encoding, expected)

    def c_locale_get_error_handler(self, locale, isolated=False, encoding=None):
        # Force the POSIX locale
        env = os.environ.copy()
        env["LC_ALL"] = locale
        env["PYTHONCOERCECLOCALE"] = "0"
        code = '\n'.join((
            'import sys',
            'def dump(name):',
            '    std = getattr(sys, name)',
            '    print("%s: %s" % (name, std.errors))',
            'dump("stdin")',
            'dump("stdout")',
            'dump("stderr")',
        ))
        args = [sys.executable, "-X", "utf8=0", "-c", code]
        if isolated:
            args.append("-I")
        if encoding is not None:
            env['PYTHONIOENCODING'] = encoding
        else:
            env.pop('PYTHONIOENCODING', None)
        p = subprocess.Popen(args,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              env=env,
                              universal_newlines=True)
        stdout, stderr = p.communicate()
        return stdout

    def check_locale_surrogateescape(self, locale):
        out = self.c_locale_get_error_handler(locale, isolated=True)
        self.assertEqual(out,
                         'stdin: surrogateescape\n'
                         'stdout: surrogateescape\n'
                         'stderr: backslashreplace\n')

        # replace the default error handler
        out = self.c_locale_get_error_handler(locale, encoding=':ignore')
        self.assertEqual(out,
                         'stdin: ignore\n'
                         'stdout: ignore\n'
                         'stderr: backslashreplace\n')

        # force the encoding
        out = self.c_locale_get_error_handler(locale, encoding='iso8859-1')
        self.assertEqual(out,
                         'stdin: strict\n'
                         'stdout: strict\n'
                         'stderr: backslashreplace\n')
        out = self.c_locale_get_error_handler(locale, encoding='iso8859-1:')
        self.assertEqual(out,
                         'stdin: strict\n'
                         'stdout: strict\n'
                         'stderr: backslashreplace\n')

        # have no any effect
        out = self.c_locale_get_error_handler(locale, encoding=':')
        self.assertEqual(out,
                         'stdin: surrogateescape\n'
                         'stdout: surrogateescape\n'
                         'stderr: backslashreplace\n')
        out = self.c_locale_get_error_handler(locale, encoding='')
        self.assertEqual(out,
                         'stdin: surrogateescape\n'
                         'stdout: surrogateescape\n'
                         'stderr: backslashreplace\n')

    def test_c_locale_surrogateescape(self):
        self.check_locale_surrogateescape('C')

    def test_posix_locale_surrogateescape(self):
        self.check_locale_surrogateescape('POSIX')

    def test_implementation(self):
        # This test applies to all implementations equally.

        levels = {'alpha': 0xA, 'beta': 0xB, 'candidate': 0xC, 'final': 0xF}

        self.assertTrue(hasattr(sys.implementation, 'name'))
        self.assertTrue(hasattr(sys.implementation, 'version'))
        self.assertTrue(hasattr(sys.implementation, 'hexversion'))
        self.assertTrue(hasattr(sys.implementation, 'cache_tag'))

        version = sys.implementation.version
        self.assertEqual(version[:2], (version.major, version.minor))

        hexversion = (version.major << 24 | version.minor << 16 |
                      version.micro << 8 | levels[version.releaselevel] << 4 |
                      version.serial << 0)
        self.assertEqual(sys.implementation.hexversion, hexversion)

        # PEP 421 requires that .name be lower case.
        self.assertEqual(sys.implementation.name,
                         sys.implementation.name.lower())

    @test.support.cpython_only
    def test_debugmallocstats(self):
        # Test sys._debugmallocstats()
        from test.support.script_helper import assert_python_ok
        args = ['-c', 'import sys; sys._debugmallocstats()']
        ret, out, err = assert_python_ok(*args)
        self.assertIn(b"free PyDictObjects", err)

        # The function has no parameter
        self.assertRaises(TypeError, sys._debugmallocstats, True)

    @unittest.skipUnless(hasattr(sys, "getallocatedblocks"),
                         "sys.getallocatedblocks unavailable on this build")
    def test_getallocatedblocks(self):
        try:
            import _testcapi
        except ImportError:
            with_pymalloc = support.with_pymalloc()
        else:
            alloc_name = _testcapi.pymem_getallocatorsname()
            with_pymalloc = (alloc_name in ('pymalloc', 'pymalloc_debug'))

        # Some sanity checks
        a = sys.getallocatedblocks()
        self.assertIs(type(a), int)
        if with_pymalloc:
            self.assertGreater(a, 0)
        else:
            # When WITH_PYMALLOC isn't available, we don't know anything
            # about the underlying implementation: the function might
            # return 0 or something greater.
            self.assertGreaterEqual(a, 0)
        try:
            # While we could imagine a Python session where the number of
            # multiple buffer objects would exceed the sharing of references,
            # it is unlikely to happen in a normal test run.
            self.assertLess(a, sys.gettotalrefcount())
        except AttributeError:
            # gettotalrefcount() not available
            pass
        gc.collect()
        b = sys.getallocatedblocks()
        self.assertLessEqual(b, a)
        gc.collect()
        c = sys.getallocatedblocks()
        self.assertIn(c, range(b - 50, b + 50))

    @test.support.requires_type_collecting
    def test_is_finalizing(self):
        self.assertIs(sys.is_finalizing(), False)
        # Don't use the atexit module because _Py_Finalizing is only set
        # after calling atexit callbacks
        code = """if 1:
            import sys

            class AtExit:
                is_finalizing = sys.is_finalizing
                print = print

                def __del__(self):
                    self.print(self.is_finalizing(), flush=True)

            # Keep a reference in the __main__ module namespace, so the
            # AtExit destructor will be called at Python exit
            ref = AtExit()
        """
        rc, stdout, stderr = assert_python_ok('-c', code)
        self.assertEqual(stdout.rstrip(), b'True')

    @unittest.skipUnless(hasattr(sys, 'getandroidapilevel'),
                         'need sys.getandroidapilevel()')
    def test_getandroidapilevel(self):
        level = sys.getandroidapilevel()
        self.assertIsInstance(level, int)
        self.assertGreater(level, 0)

    def test_sys_tracebacklimit(self):
        code = """if 1:
            import sys
            def f1():
                1 / 0
            def f2():
                f1()
            sys.tracebacklimit = %r
            f2()
        """
        def check(tracebacklimit, expected):
            p = subprocess.Popen([sys.executable, '-c', code % tracebacklimit],
                                 stderr=subprocess.PIPE)
            out = p.communicate()[1]
            self.assertEqual(out.splitlines(), expected)

        traceback = [
            b'Traceback (most recent call last):',
            b'  File "<string>", line 8, in <module>',
            b'  File "<string>", line 6, in f2',
            b'  File "<string>", line 4, in f1',
            b'ZeroDivisionError: division by zero'
        ]
        check(10, traceback)
        check(3, traceback)
        check(2, traceback[:1] + traceback[2:])
        check(1, traceback[:1] + traceback[3:])
        check(0, [traceback[-1]])
        check(-1, [traceback[-1]])
        check(1<<1000, traceback)
        check(-1<<1000, [traceback[-1]])
        check(None, traceback)

    def test_no_duplicates_in_meta_path(self):
        self.assertEqual(len(sys.meta_path), len(set(sys.meta_path)))

    @unittest.skipUnless(hasattr(sys, "_enablelegacywindowsfsencoding"),
                         'needs sys._enablelegacywindowsfsencoding()')
    def test__enablelegacywindowsfsencoding(self):
        code = ('import sys',
                'sys._enablelegacywindowsfsencoding()',
                'print(sys.getfilesystemencoding(), sys.getfilesystemencodeerrors())')
        rc, out, err = assert_python_ok('-c', '; '.join(code))
        out = out.decode('ascii', 'replace').rstrip()
        self.assertEqual(out, 'mbcs replace')


@test.support.cpython_only
class SizeofTest(unittest.TestCase):

    def setUp(self):
        self.P = struct.calcsize('P')
        self.longdigit = sys.int_info.sizeof_digit
        import _testcapi
        self.gc_headsize = _testcapi.SIZEOF_PYGC_HEAD

    check_sizeof = test.support.check_sizeof

    def test_gc_head_size(self):
        # Check that the gc header size is added to objects tracked by the gc.
        vsize = test.support.calcvobjsize
        gc_header_size = self.gc_headsize
        # bool objects are not gc tracked
        self.assertEqual(sys.getsizeof(True), vsize('') + self.longdigit)
        # but lists are
        self.assertEqual(sys.getsizeof([]), vsize('Pn') + gc_header_size)

    def test_errors(self):
        class BadSizeof:
            def __sizeof__(self):
                raise ValueError
        self.assertRaises(ValueError, sys.getsizeof, BadSizeof())

        class InvalidSizeof:
            def __sizeof__(self):
                return None
        self.assertRaises(TypeError, sys.getsizeof, InvalidSizeof())
        sentinel = ["sentinel"]
        self.assertIs(sys.getsizeof(InvalidSizeof(), sentinel), sentinel)

        class FloatSizeof:
            def __sizeof__(self):
                return 4.5
        self.assertRaises(TypeError, sys.getsizeof, FloatSizeof())
        self.assertIs(sys.getsizeof(FloatSizeof(), sentinel), sentinel)

        class OverflowSizeof(int):
            def __sizeof__(self):
                return int(self)
        self.assertEqual(sys.getsizeof(OverflowSizeof(sys.maxsize)),
                         sys.maxsize + self.gc_headsize)
        with self.assertRaises(OverflowError):
            sys.getsizeof(OverflowSizeof(sys.maxsize + 1))
        with self.assertRaises(ValueError):
            sys.getsizeof(OverflowSizeof(-1))
        with self.assertRaises((ValueError, OverflowError)):
            sys.getsizeof(OverflowSizeof(-sys.maxsize - 1))

    def test_default(self):
        size = test.support.calcvobjsize
        self.assertEqual(sys.getsizeof(True), size('') + self.longdigit)
        self.assertEqual(sys.getsizeof(True, -1), size('') + self.longdigit)

    def test_objecttypes(self):
        # check all types defined in Objects/
        calcsize = struct.calcsize
        size = test.support.calcobjsize
        vsize = test.support.calcvobjsize
        check = self.check_sizeof
        # bool
        check(True, vsize('') + self.longdigit)
        # buffer
        # XXX
        # builtin_function_or_method
        check(len, size('4P')) # XXX check layout
        # bytearray
        samples = [b'', b'u'*100000]
        for sample in samples:
            x = bytearray(sample)
            check(x, vsize('n2Pi') + x.__alloc__())
        # bytearray_iterator
        check(iter(bytearray()), size('nP'))
        # bytes
        check(b'', vsize('n') + 1)
        check(b'x' * 10, vsize('n') + 11)
        # cell
        def get_cell():
            x = 42
            def inner():
                return x
            return inner
        check(get_cell().__closure__[0], size('P'))
        # code
        def check_code_size(a, expected_size):
            self.assertGreaterEqual(sys.getsizeof(a), expected_size)
        check_code_size(get_cell().__code__, size('6i13P'))
        check_code_size(get_cell.__code__, size('6i13P'))
        def get_cell2(x):
            def inner():
                return x
            return inner
        check_code_size(get_cell2.__code__, size('6i13P') + calcsize('n'))
        # complex
        check(complex(0,1), size('2d'))
        # method_descriptor (descriptor object)
        check(str.lower, size('3PP'))
        # classmethod_descriptor (descriptor object)
        # XXX
        # member_descriptor (descriptor object)
        import datetime
        check(datetime.timedelta.days, size('3PP'))
        # getset_descriptor (descriptor object)
        import collections
        check(collections.defaultdict.default_factory, size('3PP'))
        # wrapper_descriptor (descriptor object)
        check(int.__add__, size('3P2P'))
        # method-wrapper (descriptor object)
        check({}.__iter__, size('2P'))
        # dict
        check({}, size('nQ2P') + calcsize('2nP2n') + 8 + (8*2//3)*calcsize('n2P'))
        longdict = {1:1, 2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8}
        check(longdict, size('nQ2P') + calcsize('2nP2n') + 16 + (16*2//3)*calcsize('n2P'))
        # dictionary-keyview
        check({}.keys(), size('P'))
        # dictionary-valueview
        check({}.values(), size('P'))
        # dictionary-itemview
        check({}.items(), size('P'))
        # dictionary iterator
        check(iter({}), size('P2nPn'))
        # dictionary-keyiterator
        check(iter({}.keys()), size('P2nPn'))
        # dictionary-valueiterator
        check(iter({}.values()), size('P2nPn'))
        # dictionary-itemiterator
        check(iter({}.items()), size('P2nPn'))
        # dictproxy
        class C(object): pass
        check(C.__dict__, size('P'))
        # BaseException
        check(BaseException(), size('5Pb'))
        # UnicodeEncodeError
        check(UnicodeEncodeError("", "", 0, 0, ""), size('5Pb 2P2nP'))
        # UnicodeDecodeError
        check(UnicodeDecodeError("", b"", 0, 0, ""), size('5Pb 2P2nP'))
        # UnicodeTranslateError
        check(UnicodeTranslateError("", 0, 1, ""), size('5Pb 2P2nP'))
        # ellipses
        check(Ellipsis, size(''))
        # EncodingMap
        import codecs, encodings.iso8859_3
        x = codecs.charmap_build(encodings.iso8859_3.decoding_table)
        check(x, size('32B2iB'))
        # enumerate
        check(enumerate([]), size('n3P'))
        # reverse
        check(reversed(''), size('nP'))
        # float
        check(float(0), size('d'))
        # sys.floatinfo
        check(sys.float_info, vsize('') + self.P * len(sys.float_info))
        # frame
        import inspect
        CO_MAXBLOCKS = 20
        x = inspect.currentframe()
        ncells = len(x.f_code.co_cellvars)
        nfrees = len(x.f_code.co_freevars)
        extras = x.f_code.co_stacksize + x.f_code.co_nlocals +\
                  ncells + nfrees - 1
        check(x, vsize('5P2c4P3ic' + CO_MAXBLOCKS*'3i' + 'P' + extras*'P'))
        # function
        def func(): pass
        check(func, size('12P'))
        class c():
            @staticmethod
            def foo():
                pass
            @classmethod
            def bar(cls):
                pass
            # staticmethod
            check(foo, size('PP'))
            # classmethod
            check(bar, size('PP'))
        # generator
        def get_gen(): yield 1
        check(get_gen(), size('Pb2PPP4P'))
        # iterator
        check(iter('abc'), size('lP'))
        # callable-iterator
        import re
        check(re.finditer('',''), size('2P'))
        # list
        samples = [[], [1,2,3], ['1', '2', '3']]
        for sample in samples:
            check(sample, vsize('Pn') + len(sample)*self.P)
        # sortwrapper (list)
        # XXX
        # cmpwrapper (list)
        # XXX
        # listiterator (list)
        check(iter([]), size('lP'))
        # listreverseiterator (list)
        check(reversed([]), size('nP'))
        # int
        check(0, vsize(''))
        check(1, vsize('') + self.longdigit)
        check(-1, vsize('') + self.longdigit)
        PyLong_BASE = 2**sys.int_info.bits_per_digit
        check(int(PyLong_BASE), vsize('') + 2*self.longdigit)
        check(int(PyLong_BASE**2-1), vsize('') + 2*self.longdigit)
        check(int(PyLong_BASE**2), vsize('') + 3*self.longdigit)
        # module
        check(unittest, size('PnPPP'))
        # None
        check(None, size(''))
        # NotImplementedType
        check(NotImplemented, size(''))
        # object
        check(object(), size(''))
        # property (descriptor object)
        class C(object):
            def getx(self): return self.__x
            def setx(self, value): self.__x = value
            def delx(self): del self.__x
            x = property(getx, setx, delx, "")
            check(x, size('4Pi'))
        # PyCapsule
        # XXX
        # rangeiterator
        check(iter(range(1)), size('4l'))
        # reverse
        check(reversed(''), size('nP'))
        # range
        check(range(1), size('4P'))
        check(range(66000), size('4P'))
        # set
        # frozenset
        PySet_MINSIZE = 8
        samples = [[], range(10), range(50)]
        s = size('3nP' + PySet_MINSIZE*'nP' + '2nP')
        for sample in samples:
            minused = len(sample)
            if minused == 0: tmp = 1
            # the computation of minused is actually a bit more complicated
            # but this suffices for the sizeof test
            minused = minused*2
            newsize = PySet_MINSIZE
            while newsize <= minused:
                newsize = newsize << 1
            if newsize <= 8:
                check(set(sample), s)
                check(frozenset(sample), s)
            else:
                check(set(sample), s + newsize*calcsize('nP'))
                check(frozenset(sample), s + newsize*calcsize('nP'))
        # setiterator
        check(iter(set()), size('P3n'))
        # slice
        check(slice(0), size('3P'))
        # super
        check(super(int), size('3P'))
        # tuple
        check((), vsize(''))
        check((1,2,3), vsize('') + 3*self.P)
        # type
        # static type: PyTypeObject
        fmt = 'P2n15Pl4Pn9Pn11PIP'
        if hasattr(sys, 'getcounts'):
            fmt += '3n2P'
        s = vsize(fmt)
        check(int, s)
        # class
        s = vsize(fmt +                 # PyTypeObject
                  '3P'                  # PyAsyncMethods
                  '36P'                 # PyNumberMethods
                  '3P'                  # PyMappingMethods
                  '10P'                 # PySequenceMethods
                  '2P'                  # PyBufferProcs
                  '4P')
        class newstyleclass(object): pass
        # Separate block for PyDictKeysObject with 8 keys and 5 entries
        check(newstyleclass, s + calcsize("2nP2n0P") + 8 + 5*calcsize("nP"))
        # dict with shared keys
        check(newstyleclass().__dict__, size('nQ2P') + 5*self.P)
        o = newstyleclass()
        o.a = o.b = o.c = o.d = o.e = o.f = o.g = o.h = 1
        # Separate block for PyDictKeysObject with 16 keys and 10 entries
        check(newstyleclass, s + calcsize("2nP2n0P") + 16 + 10*calcsize("nP"))
        # dict with shared keys
        check(newstyleclass().__dict__, size('nQ2P') + 10*self.P)
        # unicode
        # each tuple contains a string and its expected character size
        # don't put any static strings here, as they may contain
        # wchar_t or UTF-8 representations
        samples = ['1'*100, '\xff'*50,
                   '\u0100'*40, '\uffff'*100,
                   '\U00010000'*30, '\U0010ffff'*100]
        asciifields = "nnbP"
        compactfields = asciifields + "nPn"
        unicodefields = compactfields + "P"
        for s in samples:
            maxchar = ord(max(s))
            if maxchar < 128:
                L = size(asciifields) + len(s) + 1
            elif maxchar < 256:
                L = size(compactfields) + len(s) + 1
            elif maxchar < 65536:
                L = size(compactfields) + 2*(len(s) + 1)
            else:
                L = size(compactfields) + 4*(len(s) + 1)
            check(s, L)
        # verify that the UTF-8 size is accounted for
        s = chr(0x4000)   # 4 bytes canonical representation
        check(s, size(compactfields) + 4)
        # compile() will trigger the generation of the UTF-8
        # representation as a side effect
        compile(s, "<stdin>", "eval")
        check(s, size(compactfields) + 4 + 4)
        # TODO: add check that forces the presence of wchar_t representation
        # TODO: add check that forces layout of unicodefields
        # weakref
        import weakref
        check(weakref.ref(int), size('2Pn2P'))
        # weakproxy
        # XXX
        # weakcallableproxy
        check(weakref.proxy(int), size('2Pn2P'))

    def check_slots(self, obj, base, extra):
        expected = sys.getsizeof(base) + struct.calcsize(extra)
        if gc.is_tracked(obj) and not gc.is_tracked(base):
            expected += self.gc_headsize
        self.assertEqual(sys.getsizeof(obj), expected)

    def test_slots(self):
        # check all subclassable types defined in Objects/ that allow
        # non-empty __slots__
        check = self.check_slots
        class BA(bytearray):
            __slots__ = 'a', 'b', 'c'
        check(BA(), bytearray(), '3P')
        class D(dict):
            __slots__ = 'a', 'b', 'c'
        check(D(x=[]), {'x': []}, '3P')
        class L(list):
            __slots__ = 'a', 'b', 'c'
        check(L(), [], '3P')
        class S(set):
            __slots__ = 'a', 'b', 'c'
        check(S(), set(), '3P')
        class FS(frozenset):
            __slots__ = 'a', 'b', 'c'
        check(FS(), frozenset(), '3P')
        from collections import OrderedDict
        class OD(OrderedDict):
            __slots__ = 'a', 'b', 'c'
        check(OD(x=[]), OrderedDict(x=[]), '3P')

    def test_pythontypes(self):
        # check all types defined in Python/
        size = test.support.calcobjsize
        vsize = test.support.calcvobjsize
        check = self.check_sizeof
        # _ast.AST
        import _ast
        check(_ast.AST(), size('P'))
        try:
            raise TypeError
        except TypeError:
            tb = sys.exc_info()[2]
            # traceback
            if tb is not None:
                check(tb, size('2P2i'))
        # symtable entry
        # XXX
        # sys.flags
        check(sys.flags, vsize('') + self.P * len(sys.flags))

    def test_asyncgen_hooks(self):
        old = sys.get_asyncgen_hooks()
        self.assertIsNone(old.firstiter)
        self.assertIsNone(old.finalizer)

        firstiter = lambda *a: None
        sys.set_asyncgen_hooks(firstiter=firstiter)
        hooks = sys.get_asyncgen_hooks()
        self.assertIs(hooks.firstiter, firstiter)
        self.assertIs(hooks[0], firstiter)
        self.assertIs(hooks.finalizer, None)
        self.assertIs(hooks[1], None)

        finalizer = lambda *a: None
        sys.set_asyncgen_hooks(finalizer=finalizer)
        hooks = sys.get_asyncgen_hooks()
        self.assertIs(hooks.firstiter, firstiter)
        self.assertIs(hooks[0], firstiter)
        self.assertIs(hooks.finalizer, finalizer)
        self.assertIs(hooks[1], finalizer)

        sys.set_asyncgen_hooks(*old)
        cur = sys.get_asyncgen_hooks()
        self.assertIsNone(cur.firstiter)
        self.assertIsNone(cur.finalizer)


def test_main():
    test.support.run_unittest(SysModuleTest, SizeofTest)

if __name__ == "__main__":
    test_main()
