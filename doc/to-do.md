Stuff to do for Qy
==================

Miscellaneous
-------------

* specify sane numeric coercion rules
* implement sane numeric coercion rules
* document sane numeric coercion rules
* unit-test sane numeric coercion rules

Major efforts
-------------

* build concise array operations; analogues to numpy operations

An alternate if-then-else syntax?
---------------------------------

    @qy.if_()
    def _():
        yield m == n

        # ...

        yield m == 0.0

        # ...

    @qy.if_(m == n)
    def _():
        # ...
    @_.else()
    def _():
        # ...

