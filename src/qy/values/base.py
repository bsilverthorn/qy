"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

__all__ = [
    "CoercionError",
    "Value",
    ]

import numpy
import qy
import qy.llvm as llvm

class CoercionError(TypeError):
    """
    Failed to coerce a value to that of another type.
    """

    def __init__(self, from_type, to_type):
        """
        Initialize.
        """

        TypeError.__init__(
            self,
            "don't know how to convert from %s to %s" % (from_type, to_type),
            )

class Value(object):
    """
    Value in the wrapper language.
    """

    def __init__(self, value):
        """
        Initialize.
        """

        if not isinstance(value, llvm.Value):
            raise TypeError("Value constructor requires an LLVM value")
        elif self.kind is not None and value.type.kind != self.kind:
            raise TypeError(
                "cannot covariable's nstruct an %s instance from a %s value",
                type(self).__name__,
                type(value).__name,
                )

        self._value = value

    def __str__(self):
        """
        Return a readable string representation of this value.
        """

        return str(self._value)

    def __repr__(self):
        """
        Return a parseable string representation of this value.
        """

        return "Value.from_low(%s)" % repr(self._value)

    def __lt__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __le__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __gt__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __ge__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __eq__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __ne__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __add__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __sub__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __mul__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __div__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __floordiv__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __mod__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __divmod__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __pow__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __and__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __xor__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __or__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __lshift__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __rshift__(self, other):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __neg__(self):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __pos__(self):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __abs__(self):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __invert__(self):
        """
        XXX.
        """

        raise TypeError("%s value does not define this operator" % type(self).__name__)

    def __radd__(self, other):
        """
        Apply the "+" operator.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return other + self

    def __rsub__(self, other):
        """
        Apply the "-" operator.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return other - self

    def __rmul__(self, other):
        """
        Apply the "*" operator.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return other * self

    def __rdiv__(self, other):
        """
        Apply the "/" operator.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return other / self

    def __rmod__(self, other):
        """
        Apply the "%" operator.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return other % self

    def __rdivmod__(self, other):
        """
        Apply the "divmod" operator.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return divmod(other, self)

    def __rpow__(self, other):
        """
        Apply the "**" operator.
        """

        raise TypeError("%s value does not have right-operator ** defined" % type(self).__name__)

    def __rlshift__(self, other):
        """
        Apply the "<<" operator.
        """

        raise TypeError("%s value does not have right-operator << defined" % type(self).__name__)

    def __rrshift__(self, other):
        """
        Apply the ">>" operator.
        """

        raise TypeError("%s value does not have right-operator >> defined" % type(self).__name__)

    def __rand__(self, other):
        """
        Apply the "&" operator.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return other & self

    def __rxor__(self, other):
        """
        Apply the "^" operator.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return other ^ self

    def __ror__(self, other):
        """
        Apply the "|" operator.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return other | self

    def store(self, pointer):
        """
        Store this value to the specified pointer.
        """

        return qy.get().builder.store(self._value, pointer._value)

    @property
    def low(self):
        """
        The associated LLVM value.
        """

        return self._value

    @property
    def type_(self):
        """
        The type of the associated LLVM value.
        """

        return self._value.type

    @property
    def kind(self):
        """
        Enum describing the general kind of this value, or None.
        """

        return None

    @staticmethod
    def from_any(value):
        """
        Build a Qy value from some value.
        """

        if isinstance(value, Value):
            return value
        elif isinstance(value, llvm.Value):
            return Value.from_low(value)
        elif isinstance(value, int):
            return \
                Value.from_low(
                    llvm.Constant.int(
                        llvm.Type.int(numpy.dtype(int).itemsize * 8),
                        int(value),
                        ),
                    )
        elif isinstance(value, long):
            return \
                Value.from_low(
                    llvm.Constant.int(
                        llvm.Type.int(numpy.dtype(long).itemsize * 8),
                        long(value),
                        ),
                    )
        elif isinstance(value, float):
            return \
                Value.from_low(
                    llvm.Constant.real(llvm.Type.double(), value),
                    )
        elif isinstance(value, bool):
            return Value.from_low(llvm.Constant.int(llvm.Type.int(1), int(value)))
        else:
            raise TypeError("cannot build value from \"%s\" instance" % type(value))

    @staticmethod
    def from_low(value):
        """
        Build a Qy value from an LLVM value.
        """

        # sanity
        if not isinstance(value, llvm.Value):
            raise TypeError("value is not an LLVM value")

        # generate an appropriate value type
        if value.type.kind == llvm.TYPE_INTEGER:
            return qy.IntegerValue(value)
        elif value.type.kind == llvm.TYPE_DOUBLE:
            return qy.RealValue(value)
        elif value.type.kind == llvm.TYPE_POINTER:
            return qy.PointerValue(value)
        else:
            return qy.Value(value)

