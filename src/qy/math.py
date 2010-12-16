"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

import qy

def ln_gamma(x):
    """
    Compute the log of the gamma function.
    """

    @qy.Function.define_once(float, [float])
    def ln_gamma_d(x_in):
        _ln_gamma(x_in)

    return ln_gamma_d(x)

def _ln_gamma(x):
    """
    Emit the log-gamma computation.

    This implementation is adapted from the same Cody & Stoltz netlib code on
    which everyone bases their implementation.
    """

    import math

    a = qy.value_from_any(0.6796875)

    @qy.if_((x <= 0.5) | ((x > a) & (x <= 1.5)))
    def _():
        result = qy.stack_allocate(float)
        input_ = qy.stack_allocate(float)

        p1 = [ 
            4.945235359296727046734888e0,
            2.018112620856775083915565e2,
            2.290838373831346393026739e3,
            1.131967205903380828685045e4,
            2.855724635671635335736389e4,
            3.848496228443793359990269e4,
            2.637748787624195437963534e4,
            7.225813979700288197698961e3,
            ]
        q1 = [
            6.748212550303777196073036e1,
            1.113332393857199323513008e3,
            7.738757056935398733233834e3,
            2.763987074403340708898585e4,
            5.499310206226157329794414e4,
            6.161122180066002127833352e4,
            3.635127591501940507276287e4,
            8.785536302431013170870835e3,
            ]

        @qy.if_else(x <= 0.5)
        def _(then):
            if then:
                (-qy.log(x)).store(result)

                @qy.if_(x + 1.0 == 1.0)
                def _():
                    qy.return_(result.load())

                x.store(input_)
            else:
                qy.value_from_any(0.0).store(result)

                (x - 1.0).store(input_)

        y    = input_.load()
        xnum = 0.0
        xden = 1.0

        for (p, q) in zip(p1, q1):
            xnum = xnum * y + p
            xden = xden * y + q

        d1 = -5.772156649015328605195174e-1

        qy.return_(result.load() + y * (d1 + y * (xnum / xden)))

    @qy.if_((x <= a) | ((x > 1.5) & (x <= 4)))
    def _():
        result = qy.stack_allocate(float)
        input_ = qy.stack_allocate(float)

        p2 = [
            4.974607845568932035012064e0,
            5.424138599891070494101986e2,
            1.550693864978364947665077e4,
            1.847932904445632425417223e5,
            1.088204769468828767498470e6,
            3.338152967987029735917223e6,
            5.106661678927352456275255e6,
            3.074109054850539556250927e6,
            ]
        q2 = [
            1.830328399370592604055942e2,
            7.765049321445005871323047e3,
            1.331903827966074194402448e5,
            1.136705821321969608938755e6,
            5.267964117437946917577538e6,
            1.346701454311101692290052e7,
            1.782736530353274213975932e7,
            9.533095591844353613395747e6,
            ]

        @qy.if_else(x <= a)
        def _(then):
            if then:
                (-qy.log(x)).store(result)

                (x - 1.0).store(input_)
            else:
                qy.value_from_any(0.0).store(result)

                (x - 2.0).store(input_)

        y    = input_.load()
        xnum = 0.0
        xden = 1.0

        for (p, q) in zip(p2, q2):
            xnum = xnum * y + p
            xden = xden * y + q

        d2 = 4.227843350984671393993777e-1

        qy.return_(result.load() + y * (d2 + y * (xnum / xden)))

    @qy.if_(x <= 12)
    def _():
        p4 = [
            1.474502166059939948905062e4 ,
            2.426813369486704502836312e6 ,
            1.214755574045093227939592e8 ,
            2.663432449630976949898078e9 ,
            2.940378956634553899906876e10,
            1.702665737765398868392998e11,
            4.926125793377430887588120e11,
            5.606251856223951465078242e11,
            ]
        q4 = [
            2.690530175870899333379843e3 ,
            6.393885654300092398984238e5 ,
            4.135599930241388052042842e7 ,
            1.120872109616147941376570e9 ,
            1.488613728678813811542398e10,
            1.016803586272438228077304e11,
            3.417476345507377132798597e11,
            4.463158187419713286462081e11,
            ]

        y    = x - 4.0
        xnum = 0.0
        xden = -1.0

        for (p, q) in zip(p4, q4):
            xnum = xnum * y + p
            xden = xden * y + q

        d4 = 1.791759469228055000094023e0

        qy.return_(d4 + y * (xnum / xden))

    # else
    cc = [
        -1.910444077728e-03           ,
        8.4171387781295e-04           ,
        -5.952379913043012e-04        ,
        7.93650793500350248e-04       ,
        -2.777777777777681622553e-03  ,
        8.333333333333333331554247e-02,
        ]

    y    = qy.log(x)
    r    = x * (y - 1.0) - y * 0.5 + 0.9189385332046727417803297
    s    = 1.0 / x
    z    = s * s
    xnum = 5.7083835261e-03

    for c in cc:
        xnum = xnum * z + c

    qy.return_(r + xnum * s)

def ln_factorial(n):
    """
    Compute the log of the factorial function.
    """

    return ln_gamma(n + 1.0)

def ln_choose(n, m):
    """
    Compute the log of the choose function.
    """

    @qy.Function.define_once(float, [float, float])
    def ln_choose_d(n, m):
        @qy.if_else((m == n) | (m == 0.0))
        def _(then):
            if then:
                qy.return_(0.0)
            else:
                k = qy.Variable(float)

                @qy.if_else(m * 2.0 > n)
                def _(then):
                    if then:
                        k.set(n - m)
                    else:
                        k.set(m)

                result =                         \
                      ln_factorial(n)            \
                    - ln_factorial(k.value)      \
                    - ln_factorial(n - k.value)

                qy.return_(result)

    return ln_choose_d(n, m)

