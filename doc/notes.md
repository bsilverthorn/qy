Qy design notes
===============

Not primarily intended for public consumption.

Module layout
-------------

The core statements and types are available directly from the qy module, as in

<code>
    import qy

    @qy.for(N)
    def _(i):
        ...
</code>

These methods are proxies defined in `qy.module`.

