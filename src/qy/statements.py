"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

names_to_wrap = [
    "value_from_any",
    "type_from_any",
    "string_literal",
    "if_",
    "if_else",
    "for_",
    "select",
    "random",
    "random_int",
    "log",
    "log1p",
    "exp",
    "python",
    "py_import",
    "py_scope",
    "py_tuple",
    "py_inc_ref",
    "py_dec_ref",
    "py_print",
    "py_printf",
    "py_check_null",
    "heap_allocate",
    "stack_allocate",
    "assert_",
    "return_",
    "this_builder",
    ]

__all__ = names_to_wrap

from qy import Qy

def wrap_language_call(name):
    """
    Wrap a call to the active Qy instance.
    """

    # XXX don't obscure the arguments of the wrapped method

    def wrapper(*args, **kwargs):
        """
        Call a method of the active Qy instance.
        """

        return getattr(Qy.get_active(), name)(*args, **kwargs)

    globals()[name] = wrapper

for name in names_to_wrap:
    wrap_language_call(name)

