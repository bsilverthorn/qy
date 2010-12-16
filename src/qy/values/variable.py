"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

import qy

class Variable(object):
    """
    Mutable value.
    """

    def __init__(self, type_):
        """
        Initialize.
        """

        self._location = qy.stack_allocate(type_)

    def __lt__(self, other):
        """
        XXX.
        """

        return self._location.load() < other

    def __le__(self, other):
        """
        XXX.
        """

        return self._location.load() <= other

    def __gt__(self, other):
        """
        XXX.
        """

        return self._location.load() > other

    def __ge__(self, other):
        """
        XXX.
        """

        return self._location.load() >= other

    def __eq__(self, other):
        """
        XXX.
        """

        return self._location.load() == other

    def __ne__(self, other):
        """
        XXX.
        """

        return self._location.load() != other

    def __add__(self, other):
        """
        XXX.
        """

        return self._location.load() + other

    def __sub__(self, other):
        """
        XXX.
        """

        return self._location.load() - other

    def __mul__(self, other):
        """
        XXX.
        """

        return self._location.load() * other

    def __div__(self, other):
        """
        XXX.
        """

        return self._location.load() / other

    def __floordiv__(self, other):
        """
        XXX.
        """

        return self._location.load() // other

    def __mod__(self, other):
        """
        XXX.
        """

        return self._location.load() % other

    def __divmod__(self, other):
        """
        XXX.
        """

        return divmod(self._location.load(), other)

    def __pow__(self, other):
        """
        XXX.
        """

        return self._location.load() ** other

    def __and__(self, other):
        """
        XXX.
        """

        return self._location.load() & other

    def __xor__(self, other):
        """
        XXX.
        """

        return self._location.load() ^ other

    def __or__(self, other):
        """
        XXX.
        """

        return self._location.load() | other

    def __lshift__(self, other):
        """
        XXX.
        """

        return self._location.load() << other

    def __rshift__(self, other):
        """
        XXX.
        """

        return self._location.load() >> other

    def __neg__(self):
        """
        XXX.
        """

        return -self._location.load()

    def __pos__(self):
        """
        XXX.
        """

        return +self._location.load()

    def __abs__(self):
        """
        XXX.
        """

        return abs(self._location.load())

    def __invert__(self):
        """
        XXX.
        """

        return ~self._location.load()

    def __radd__(self, other):
        """
        Return other + self.
        """

        return other | self._location.load()

    def __rsub__(self, other):
        """
        XXX.
        """

        return other | self._location.load()

    def __rmul__(self, other):
        """
        """

        return other | self._location.load()

    def __rdiv__(self, other):
        """
        XXX.
        """

        return other | self._location.load()

    def __rmod__(self, other):
        """
        XXX.
        """

        return other | self._location.load()

    def __rdivmod__(self, other):
        """
        XXX.
        """

        return other | self._location.load()

    def __rpow__(self, other):
        """
        XXX.
        """

        return other | self._location.load()

    def __rlshift__(self, other):
        """
        XXX.
        """

        return other | self._location.load()

    def __rrshift__(self, other):
        """
        XXX.
        """

        return other | self._location.load()

    def __rand__(self, other):
        """
        XXX.
        """

        return other | self._location.load()

    def __rxor__(self, other):
        """
        XXX.
        """

        return other | self._location.load()

    def __ror__(self, other):
        """
        XXX.
        """

        return other | self._location.load()

    def __iadd__(self, other):
        """
        XXX.
        """

        self.set(self + other)

    def __isub__(self, other):
        """
        XXX.
        """

        self.set(self - other)

    def __imul__(self, other):
        """
        XXX.
        """

        self.set(self * other)

    def __idiv__(self, other):
        """
        XXX.
        """

        self.set(self / other)

    def __ifloordiv__(self, other):
        """
        XXX.
        """

        self.set(self // other)

    def __imod__(self, other):
        """
        XXX.
        """

        self.set(self % other)

    def __ipow__(self, other):
        """
        XXX.
        """

        self.set(self ** other)

    def __iand__(self, other):
        """
        XXX.
        """

        self.set(self & other)

    def __ixor__(self, other):
        """
        XXX.
        """

        self.set(self ^ other)

    def __ior__(self, other):
        """
        XXX.
        """

        self.set(self | other)

    def __ilshift__(self, other):
        """
        XXX.
        """

        self.set(self << other)

    def __irshift__(self, other):
        """
        XXX.
        """

        self.set(self >> other)

    def set(self, value):
        """
        Change the value of the variable.
        """

        qy.value_from_any(value).store(self._location)

        return self

    @property
    def value(self):
        """
        The current value.
        """

        return self._location.load()

    @staticmethod
    def set_to(value):
        """
        Return a new variable, initialized.
        """

        value = qy.value_from_any(value)

        return Variable(value.type_).set(value)

