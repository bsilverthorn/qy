"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

import math
import numpy
import qy

from nose.tools import (
    assert_true,
    assert_false,
    assert_equal,
    assert_raises,
    assert_almost_equal,
    )
from qy import (
    emit_and_execute,
    Object,
    )

def test_qy_python_no_arguments():
    """
    Test the python() LLVM construct without arguments.
    """

    executed = [False]

    @emit_and_execute()
    def _():
        @qy.python()
        def _():
            executed[0] = [True]

    assert_true(executed[0])

def test_qy_python_arguments():
    """
    Test the python() LLVM construct with arguments.
    """

    values = []

    @emit_and_execute()
    def _():
        @qy.for_(8)
        def _(i):
            @qy.python(i)
            def _(j):
                values.append(j)

    assert_equal(values, range(8))

def test_qy_python_exception():
    """
    Test exception handling in the python() LLVM construct.
    """

    class ExpectedException(Exception):
        pass

    def should_raise():
        @emit_and_execute()
        def _():
            @qy.python()
            def _():
                raise ExpectedException()

    assert_raises(ExpectedException, should_raise)

def test_qy_python_exception_short_circuiting():
    """
    Test short-circuiting of exceptions in the python() LLVM construct.
    """

    class ExpectedException(Exception):
        pass

    def should_raise():
        @emit_and_execute()
        def _():
            @qy.python()
            def _():
                raise ExpectedException()

            @qy.python()
            def _():
                assert_true(False, "control flow was not short-circuited")

    assert_raises(ExpectedException, should_raise)

def test_qy_if_():
    """
    Test the qy-LLVM if_() construct.
    """

    bad = [True]

    @emit_and_execute()
    def _():
        @qy.if_(True)
        def _():
            @qy.python()
            def _():
                del bad[:]

    assert_false(bad)

    @emit_and_execute()
    def _():
        @qy.if_(False)
        def _():
            @qy.python()
            def _():
                assert_true(False)

def test_qy_if_else():
    """
    Test the qy-LLVM if_else() construct.
    """

    bad = [True]

    @emit_and_execute()
    def _():
        @qy.if_else(True)
        def _(then):
            if then:
                @qy.python()
                def _():
                    del bad[:]
            else:
                @qy.python()
                def _():
                    assert_true(False)

    assert_false(bad)

    bad = [True]

    @emit_and_execute()
    def _():
        @qy.if_else(False)
        def _(then):
            if then:
                @qy.python()
                def _():
                    assert_true(False)
            else:
                @qy.python()
                def _():
                    del bad[:]

    assert_false(bad)

def test_qy_for_():
    """
    Test the qy-LLVM for_() loop construct.
    """

    count      = 128
    iterations = [0]

    @emit_and_execute()
    def _():
        @qy.for_(count)
        def _(_):
            @qy.python()
            def _():
                iterations[0] += 1

    assert_equal(iterations[0], count)

def test_qy_object_basics():
    """
    Test basic operations on LLVM-wrapped Python objects.
    """

    result = [None]
    text   = "testing"

    def do_function(string_py):
        result[0] = string_py

    @emit_and_execute()
    def _():
        do     = Object.from_object(do_function)
        string = Object.from_string(text)

        do(string)

    assert_equal(result, [text])

def test_qy_py_print():
    """
    Test the py_print() LLVM construct with arguments.
    """

    import sys

    from cStringIO import StringIO

    old_stdout = sys.stdout

    try:
        new_stdout = StringIO()
        sys.stdout = new_stdout

        @emit_and_execute()
        def _():
            qy.py_print("test text\n")
    finally:
        sys.stdout = old_stdout

    assert_equal(new_stdout.getvalue(), "test text\n")

def test_qy_py_printf():
    """
    Test the py_printf() LLVM construct with arguments.
    """

    import sys

    from cStringIO import StringIO

    old_stdout = sys.stdout

    try:
        new_stdout = StringIO()
        sys.stdout = new_stdout

        @emit_and_execute()
        def _():
            @qy.for_(8)
            def _(i):
                qy.py_printf("i = %i\n", i)
    finally:
        sys.stdout = old_stdout

    assert_equal(
        new_stdout.getvalue(),
        "".join("i = %i\n" % i for i in xrange(8)),
        )

def test_qy_nested_for_():
    """
    Test the qy-LLVM for_() loop construct, nested.
    """

    count      = 32
    iterations = [0]

    @emit_and_execute()
    def _():
        @qy.for_(count)
        def _(_):
            @qy.for_(count)
            def _(_):
                @qy.python()
                def _():
                    iterations[0] += 1

    assert_equal(iterations[0], count**2)

def test_qy_assert_():
    """
    Test the qy-LLVM assert_() construct.
    """

    # should not raise
    @emit_and_execute()
    def _():
        qy.assert_(True)

    # should raise
    from qy import EmittedAssertionError

    def should_raise():
        @emit_and_execute()
        def _():
            qy.assert_(False)

    assert_raises(EmittedAssertionError, should_raise)

def test_qy_random():
    """
    Test the qy-LLVM random() construct.
    """

    count = 4096
    total = [0.0]

    @emit_and_execute()
    def _():
        @qy.for_(count)
        def _(_):
            v = qy.random()

            @qy.python(v)
            def _(v_py):
                total[0] += v_py

    assert_almost_equal(total[0] / count, 0.5, places = 1)

def test_qy_random_int():
    """
    Test the qy-LLVM random_int() construct.
    """

    count  = 32
    values = []

    @emit_and_execute()
    def _():
        @qy.for_(count)
        def _(_):
            v = qy.random_int(2)

            @qy.python(v)
            def _(v_py):
                values.append(v_py)

    assert_true(len(filter(None, values)) > 8)
    assert_true(len(filter(None, values)) < 24)

def test_qy_select():
    """
    Test the select() LLVM construct without arguments.
    """

    result = [None, None]

    @emit_and_execute()
    def _():
        v0 = qy.select(True, 3, 4)
        v1 = qy.select(False, 3, 4)

        @qy.python(v0, v1)
        def _(v0_py, v1_py):
            result[0] = v0_py
            result[1] = v1_py

    assert_equal(result[0], 3)
    assert_equal(result[1], 4)

def test_qy_is_nan():
    """
    Test LLVM real-value is_nan property.
    """

    @emit_and_execute()
    def _():
        a = qy.value_from_any(-0.000124992188151).is_nan
        b = qy.value_from_any(numpy.nan).is_nan

        @qy.python(a, b)
        def _(a_py, b_py):
            assert_false(a_py)
            assert_true(b_py)

def test_qy_log():
    """
    Test the LLVM log() intrinsic wrapper.
    """

    @emit_and_execute()
    def _():
        v0 = qy.log(math.e)

        @qy.python(v0)
        def _(v0_py):
            assert_equal(v0_py, 1.0)

def test_qy_log1p():
    """
    Test the LLVM log1p() construct.
    """

    @emit_and_execute()
    def _():
        v0 = qy.log1p(math.e - 1.0)

        @qy.python(v0)
        def _(v0_py):
            assert_equal(v0_py, 1.0)

def test_qy_exp():
    """
    Test the LLVM exp() intrinsic wrapper.
    """

    @emit_and_execute()
    def _():
        v0 = qy.exp(1.0)

        @qy.python(v0)
        def _(v0_py):
            assert_equal(v0_py, math.e)

