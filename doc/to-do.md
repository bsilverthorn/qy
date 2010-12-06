Stuff to do for Qy
==================

Miscellaneous
-------------

* are module being entirely cleaned up?

Major efforts
-------------

* build concise array operations; analogues to numpy operations

Numeric coercion rules
----------------------

* specify sane numeric coercion rules
* implement sane numeric coercion rules
* document sane numeric coercion rules
* unit-test sane numeric coercion rules

One (attractive) option is to disallow numeric coercion exception *from*
Python constants.

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

Region-based exceptional memory deallocation
--------------------------------------------

Since exceptions thrown from Python give Qy code no opportunity to perform
cleanup, if an exception occurs, we need to automatically deallocate any memory
heap-allocated by Qy code:

* ensure that we have access to the APR
* allocate the memory pool
* emit the memory pool destructor
* and register it with the module destructors
* ensure that module destructors are run

