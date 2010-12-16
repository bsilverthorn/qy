"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

import qy
import qy.llvm as llvm

class RealValue(qy.Value):
    """
    Integer value in the wrapper language.
    """

    def __eq__(self, other):
        """
        Return the result of an equality comparison.
        """

        return \
            qy.Value.from_low(
                qy.get().builder.fcmp(
                    llvm.FCMP_OEQ,
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
                qy.get().builder.fcmp(
                    llvm.FCMP_OGT,
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
                qy.get().builder.fcmp(
                    llvm.FCMP_OGE,
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
                qy.get().builder.fcmp(
                    llvm.FCMP_OLT,
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
                qy.get().builder.fcmp(
                    llvm.FCMP_OLE,
                    self._value,
                    qy.value_from_any(other).cast_to(self.type_)._value,
                    ),
                )

    def __neg__(self):
        """
        Return the result of a negation.
        """

        return self * -1.0

    def __abs__(self):
        """
        Return the absolute value of this value.
        """

        return qy.select(self > 0.0, self, -self)

    def __add__(self, other):
        """
        Return the result of an addition.
        """

        other = qy.value_from_any(other).cast_to(self.type_)
        value = RealValue(qy.get().builder.fadd(self._value, other._value))

        if qy.get().test_for_nan:
            qy.assert_(~value.is_nan, "result of %s + %s is not a number", other, self)

        return value

    def __sub__(self, other):
        """
        Return the result of a subtraction.
        """

        other = qy.value_from_any(other).cast_to(self.type_)
        value = RealValue(qy.get().builder.fsub(self._value, other._value))

        if qy.get().test_for_nan:
            qy.assert_(~value.is_nan, "result of %s - %s is not a number", other, self)

        return value

    def __mul__(self, other):
        """
        Return the result of a multiplication.
        """

        other = qy.value_from_any(other).cast_to(self.type_)
        value = RealValue(qy.get().builder.fmul(self._value, other._value))

        if qy.get().test_for_nan:
            qy.assert_(~value.is_nan, "result of %s * %s is not a number", other, self)

        return value

    def __div__(self, other):
        """
        Return the result of a division.
        """

        other = qy.value_from_any(other).cast_to(self.type_)
        value = RealValue(qy.get().builder.fdiv(self._value, other._value))

        if qy.get().test_for_nan:
            qy.assert_(~value.is_nan, "result of %s / %s is not a number", other, self)

        return value

    @property
    def is_nan(self):
        """
        Test for nan.
        """

        return \
            qy.Value.from_low(
                qy.get().builder.fcmp(
                    llvm.FCMP_UNO,
                    self._value,
                    self._value,
                    ),
                )

    def cast_to(self, type_, name = ""):
        """
        Cast this value to the specified type.
        """

        # XXX support more casts

        type_     = qy.type_from_any(type_)
        low_value = None

        if type_.kind == llvm.TYPE_DOUBLE:
            if self.type_.kind == llvm.TYPE_DOUBLE:
                low_value = self._value
        if type_.kind == llvm.TYPE_INTEGER:
            low_value = qy.get().builder.fptosi(self._value, type_, name)

        if low_value is None:
            raise CoercionError(self.type_, type_)
        else:
            return qy.Value.from_low(low_value)

    def to_python(self):
        """
        Emit conversion of this value to a Python object.
        """

        from qy import (
            Function,
            object_ptr_type,
            )

        float_from_double = Function.named("PyFloat_FromDouble", object_ptr_type, [float])

        return float_from_double(self._value)

