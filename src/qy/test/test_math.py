"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

import qy

from nose.tools import assert_almost_equal
from qy         import emit_and_execute

def test_ln_gamma():
    """
    Test computation of the log-gamma function.
    """

    from qy.math       import ln_gamma
    from scipy.special import gammaln

    def assert_ln_gamma_ok(x):
        @qy.python(ln_gamma(x))
        def _(v):
            assert_almost_equal(v, gammaln(x))

    @emit_and_execute()
    def _():
        assert_ln_gamma_ok(0.01 )
        assert_ln_gamma_ok(0.25 )
        assert_ln_gamma_ok(0.60 )
        assert_ln_gamma_ok(0.75 )
        assert_ln_gamma_ok(1.0  )
        assert_ln_gamma_ok(10.0 )
        assert_ln_gamma_ok(100.0)
        assert_ln_gamma_ok(1e6  )

def test_ln_factorial():
    """
    Test computation of the log-factorial function.
    """

    from math import (
        log,
        factorial,
        )
    from qy.math import ln_factorial

    def assert_ln_factorial_ok(x):
        @qy.python(ln_factorial(x))
        def _(v):
            assert_almost_equal(v, log(factorial(x)))

    @emit_and_execute()
    def _():
        assert_ln_factorial_ok(0.0)
        assert_ln_factorial_ok(1.0)
        assert_ln_factorial_ok(4.0)
        assert_ln_factorial_ok(16.0)
        assert_ln_factorial_ok(128.0)

def test_ln_choose():
    """
    Test computation of the log-choose function.
    """

    from math import (
        log,
        factorial,
        )
    from qy.math import ln_choose

    def choose(n, k):
        """
        The naive choose function.
        """

        return factorial(n) / (factorial(k) * factorial(n - k))

    def assert_ln_choose_ok(n, k):
        @qy.python(ln_choose(n, k))
        def _(v):
            assert_almost_equal(v, log(choose(n, k)))

    @emit_and_execute()
    def _():
        assert_ln_choose_ok(1.0, 1.0)
        assert_ln_choose_ok(2.0, 1.0)
        assert_ln_choose_ok(2.0, 2.0)
        assert_ln_choose_ok(8.0, 2.0)

