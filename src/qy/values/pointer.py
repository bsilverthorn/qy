"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

__all__ = [
    "PointerValue",
    ]

import qy
import qy.llvm as llvm

class PointerValue(qy.Value):
    """
    Pointer value in the wrapper language.
    """

    def __eq__(self, other):
        """
        Return the result of an equality comparison.
        """

        return \
            qy.Value.from_low(
                qy.get().builder.icmp(
                    llvm.ICMP_EQ,
                    qy.get().builder.ptrtoint(self._value, qy.iptr_type),
                    qy.value_from_any(other).cast_to(qy.iptr_type)._value,
                    ),
                )

    def load(self, name = ""):
        """
        Load the value pointed to by this pointer.
        """

        return \
            qy.Value.from_low(
                qy.get().builder.load(self._value, name = name),
                )

    def gep(self, *indices):
        """
        Return a pointer to a component.
        """

        return \
            qy.Value.from_low(
                qy.get().builder.gep(
                    self._value,
                    [qy.Value.from_any(i)._value for i in indices],
                    ),
                )

    def to_python(self):
        """
        Build a Python-compatible argument value.
        """

        if self.type_ == qy.object_ptr_type:
            return self._value
        else:
            raise TypeError("unknown to-Python conversion for %s" % self.type_)

    def cast_to(self, type_, name = ""):
        """
        Cast this value to the specified type.
        """

        # XXX support more casts

        type_     = qy.type_from_any(type_)
        low_value = None

        if type_.kind == llvm.TYPE_POINTER:
            low_value = qy.get().builder.bitcast(self._value, type_, name)
        elif type_.kind == llvm.TYPE_INTEGER:
            if type_.width == qy.iptr_type.width:
                low_value = qy.get().builder.ptrtoint(self._value, type_, name)

        if low_value is None:
            raise CoercionError(self.type_, type_)
        else:
            return qy.Value.from_any(low_value)

