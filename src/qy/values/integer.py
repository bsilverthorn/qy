"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

__all__ = [
    "IntegerValue",
    ]

import qy
import qy.llvm as llvm

class IntegerValue(qy.Value):
    """
    Integer value in the wrapper language.
    """

    def __invert__(self):
        """
        Return the result of bitwise inversion.
        """

        return qy.get().builder.xor(self._value, LLVM_Constant.int(self.type_, -1))

    def __eq__(self, other):
        """
        Return the result of an equality comparison.
        """

        return \
            qy.Value.from_low(
                qy.get().builder.icmp(
                    llvm.ICMP_EQ,
                    self._value,
                    qy.value_from_any(other)._value,
                    ),
                )

    def __gt__(self, other):
        """
        Return the result of a greater-than comparison.
        """

        return \
            qy.Value.from_low(
                qy.get().builder.icmp(
                    llvm.ICMP_SGT,
                    self._value,
                    qy.value_from_any(other).cast_to(self.type_)._value,
                    ),
                )

    def __ge__(self, other):
        """
        Return the result of a greater-than-or-equal comparison.
        """

        return \
            qy.Value.from_low(
                qy.get().builder.icmp(
                    llvm.ICMP_SGE,
                    self._value,
                    qy.value_from_any(other).cast_to(self.type_)._value,
                    ),
                )

    def __lt__(self, other):
        """
        Return the result of a less-than comparison.
        """

        return \
            qy.Value.from_low(
                qy.get().builder.icmp(
                    llvm.ICMP_SLT,
                    self._value,
                    qy.value_from_any(other).cast_to(self.type_)._value,
                    ),
                )

    def __le__(self, other):
        """
        Return the result of a less-than-or-equal comparison.
        """

        return \
            qy.Value.from_low(
                qy.get().builder.icmp(
                    llvm.ICMP_SLE,
                    self._value,
                    qy.value_from_any(other).cast_to(self.type_)._value,
                    ),
                )

    def __add__(self, other):
        """
        Return the result of an addition.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(qy.get().builder.add(self._value, other._value))

    def __sub__(self, other):
        """
        Return the result of a subtraction.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(qy.get().builder.sub(self._value, other._value))

    def __mul__(self, other):
        """
        Return the result of a multiplication.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(qy.get().builder.mul(self._value, other._value))

    def __div__(self, other):
        """
        Return the result of a division.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(qy.get().builder.sdiv(self._value, other._value))

    def __mod__(self, other):
        """
        Return the remainder of a division.

        Note that this operation performs C-style, not Python-style, modulo.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(qy.get().builder.srem(self._value, other._value))

    def __and__(self, other):
        """
        Return the result of a bitwise and.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(qy.get().builder.and_(self._value, other._value))

    def __xor__(self, other):
        """
        Return the result of a bitwise xor.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(qy.get().builder.xor(self._value, other._value))

    def __or__(self, other):
        """
        Return the result of a bitwise or.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(qy.get().builder.or_(self._value, other._value))

    def cast_to(self, type_, name = ""):
        """
        Cast this value to the specified type.
        """

        # XXX cleanly handle signedness somehow (explicit "signed" qy value?)

        type_     = qy.type_from_any(type_)
        low_value = None

        if type_.kind == llvm.TYPE_DOUBLE:
            low_value = qy.get().builder.sitofp(self._value, type_, name)
        elif type_.kind == llvm.TYPE_INTEGER:
            if self.type_.width == type_.width:
                low_value = self._value
            elif self.type_.width < type_.width:
                low_value = qy.get().builder.sext(self._value, type_, name)
            elif self.type_.width > type_.width:
                low_value = qy.get().builder.trunc(self._value, type_, name)

        if low_value is None:
            raise CoercionError(self.type_, type_)
        else:
            return qy.Value.from_any(low_value)

    def to_python(self):
        """
        Emit conversion of this value to a Python object.
        """

        int_from_long = Function.named("PyInt_FromLong", object_ptr_type, [ctypes.c_long])

        return int_from_long(self._value)

