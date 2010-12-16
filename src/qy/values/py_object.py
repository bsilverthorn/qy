"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

import qy
import qy.llvm as llvm

class Object(qy.PointerValue):
    """
    Interact with Python objects from Qy.
    """

    def __call__(self, *arguments):
        """
        Emit a Python call.
        """

        from qy import (
            Function,
            object_ptr_type,
            )

        arguments = map(qy.value_from_any, arguments)

        @Function.define(
            llvm.Type.void(),
            [qy.object_ptr_type] + [a.type_ for a in arguments],
            )
        def invoke_python(*inner_arguments):
            from qy import constant_pointer_to

            call_object = \
                Function.named(
                    "PyObject_CallObject",
                    object_ptr_type,
                    [object_ptr_type, object_ptr_type],
                    )

            argument_tuple = qy.py_tuple(*inner_arguments[1:])
            call_result    = call_object(inner_arguments[0], argument_tuple)

            qy.py_dec_ref(argument_tuple)
            qy.py_check_null(call_result)
            qy.py_dec_ref(call_result)
            qy.return_()

        invoke_python(self, *arguments)

    def get(self, name):
        """
        Get an attribute.
        """

        object_ptr_type = qy.object_ptr_type

        get_attr = \
            Function.named(
                "PyObject_GetAttrString",
                object_ptr_type,
                [object_ptr_type, llvm.Type.pointer(llvm.Type.int(8))],
                )

        result = get_attr(self, qy.string_literal(name))

        qy.py_check_null(result)

        return Object(result._value)

    @staticmethod
    def from_object(instance):
        """
        Build a Object for a Python object.
        """

        from qy import constant_pointer_to

        return Object(constant_pointer_to(instance, qy.object_ptr_type))

    @staticmethod
    def from_string(string):
        """
        Build a Object for a Python string object.
        """

        py_from_string = \
            Function.named(
                "PyString_FromString",
                object_ptr_type,
                [llvm.Type.pointer(llvm.Type.int(8))],
                )

        return Object(py_from_string(qy.string_literal(string))._value)

class ObjectScope(object):
    """
    Define the scope of allocated Python objects.
    """

    # XXX unimplemented; we're leaking Python objects
