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
        assert_ln_gamma_ok(0.75 )
        assert_ln_gamma_ok(1.0  )
        assert_ln_gamma_ok(10.0 )
        assert_ln_gamma_ok(100.0)
        assert_ln_gamma_ok(1e6  )

