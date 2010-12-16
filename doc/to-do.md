Stuff to do for Qy
==================

Roadmaps
--------

### Path to version 0.1

(1) first reorg: split out the value classes
(2) improve the StridedArray integration
(3) build the type system
(4) make pip/easy\_installable (ideally via cmake)
(5) upload to PyPI
(6) write tutorial documentation on github

### Path to version 0.2

(1) set up automated benchmarks with versus-numpy support
(2) pick and meet a code coverage target
(3) set up continuous integration tests
(4) generate reference documentation from source

Miscellaneous
-------------

### Bulleted

* are modules being entirely cleaned up?
* support StridedArray transport *into* Python
* build concise array operations; analogues to numpy operations

### Numeric coercion rules

* specify sane numeric coercion rules
* implement sane numeric coercion rules
* document sane numeric coercion rules
* unit-test sane numeric coercion rules

One (attractive) option is to disallow numeric coercion except *from* Python
constants.

### An alternate if-then-else syntax?

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

### Region-based exceptional memory deallocation

Since exceptions thrown from Python give Qy code no opportunity to perform
cleanup, if an exception occurs, we need to automatically deallocate any memory
heap-allocated by Qy code:

* ensure that we have access to the APR
* allocate the memory pool
* emit the memory pool destructor
* and register it with the module destructors
* ensure that module destructors are run

