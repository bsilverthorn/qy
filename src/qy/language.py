"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

import ctypes
import numpy
import llvm.core
import qy

from contextlib import contextmanager
from llvm.core  import (
    Type           as LLVM_Type,
    Value          as LLVM_Value,
    Module         as LLVM_Module,
    Builder        as LLVM_Builder,
    Constant       as LLVM_Constant,
    Function       as LLVM_Function,
    GlobalVariable as LLVM_GlobalVariable,
    )
from qy import iptr_type

object_type     = LLVM_Type.struct([])
object_ptr_type = LLVM_Type.pointer(object_type)

class EmittedAssertionError(AssertionError):
    """
    An assertion was tripped in generated code.
    """

    def __init__(self, message, emission_stack = None):
        """
        Initialize.
        """

        from traceback import extract_stack

        if emission_stack is None:
            emission_stack = extract_stack()[:-1]

        self._emission_stack = emission_stack

        AssertionError.__init__(self, message)

    def __str__(self):
        """
        Generate a human-readable exception message.
        """

        try:
            from traceback import format_list

            return \
                "%s\nCode generation stack:\n%s" % (
                    AssertionError.__str__(self),
                    "".join(format_list(self._emission_stack)),
                    )
        except Exception as error:
            print sys.exc_info()

    @property
    def emission_stack(self):
        """
        Return the stack at the point of assertion IR generation.
        """

        return self._emission_stack

def get_qy():
    """
    Return the currently-active Qy language instance.
    """

    return Qy.get_active()

class Qy(object):
    """
    The Qy language, configured.
    """

    _language_stack = []

    def __init__(self, module = None, test_for_nan = False):
        """
        Initialize.
        """

        # members
        if module is None:
            module = LLVM_Module.new("qy")

        self._module        = module
        self._test_for_nan  = test_for_nan
        self._literals      = {}
        self._builder_stack = []

        # make Python-support declarations
        self._module.add_type_name("PyObjectPtr", LLVM_Type.pointer(LLVM_Type.struct([])))

        with self.active():
            # add a main
            main_body = Function.new_named("main_body")

            @Function.define(internal = False)
            def main():
                """
                The true entry point.
                """

                # initialize the Python runtime (matters only for certain test scenarios)
                Function.named("Py_Initialize")()

                # prepare for exception handling
                from qy.support import size_of_jmp_buf

                context_type = LLVM_Type.array(LLVM_Type.int(8), size_of_jmp_buf())
                context      = LLVM_GlobalVariable.new(self._module, context_type, "main_context")
                setjmp       = Function.named("setjmp", int, [LLVM_Type.pointer(LLVM_Type.int(8))])

                context.linkage     = llvm.core.LINKAGE_INTERNAL
                context.initializer = LLVM_Constant.null(context_type)

                self.if_(setjmp(context) == 0)(main_body)
                self.return_()

        # prepare for user code
        body_entry = main_body._value.append_basic_block("entry")

        self._builder_stack.append(LLVM_Builder.new(body_entry))

    def value_from_any(self, value):
        """
        Return a wrapping value.
        """

        return Value.from_any(value)

    def type_from_any(self, some_type):
        """
        Return an LLVM type from some kind of type.
        """

        # XXX support for other ctypes

        from ctypes import sizeof
        from qy     import type_from_dtype

        ctype_integer_types = \
            set([
                ctypes.c_bool,
                ctypes.c_byte,
                ctypes.c_ubyte,
                ctypes.c_char,
                ctypes.c_wchar,
                ctypes.c_short,
                ctypes.c_ushort,
                ctypes.c_long,
                ctypes.c_longlong,
                ctypes.c_ulong,
                ctypes.c_ulonglong,
                ctypes.c_int8,
                ctypes.c_int16,
                ctypes.c_int32,
                ctypes.c_int64,
                ctypes.c_uint8,
                ctypes.c_uint16,
                ctypes.c_uint32,
                ctypes.c_uint64,
                ctypes.c_size_t,
                ])

        if isinstance(some_type, type):
            return type_from_dtype(numpy.dtype(some_type))
        elif isinstance(some_type, numpy.dtype):
            return type_from_dtype(some_type)
        elif isinstance(some_type, LLVM_Type):
            return some_type
        elif some_type in ctype_integer_types:
            return LLVM_Type.int(sizeof(some_type) * 8)
        else:
            raise TypeError("cannot build type from \"%s\" instance" % type(some_type))

    def string_literal(self, string):
        """
        Define a new string literal.
        """

        if string not in self._literals:
            name  = "literal%i" % len(self._literals)
            value = \
                Value.from_low(
                    LLVM_GlobalVariable.new(
                        self.module,
                        LLVM_Type.array(LLVM_Type.int(8), len(string) + 1),
                        name,
                        ),
                    )

            value._value.linkage     = llvm.core.LINKAGE_INTERNAL
            value._value.initializer = LLVM_Constant.stringz(string)

            self._literals[string] = value

            return value
        else:
            return self._literals[string]

    def if_(self, condition):
        """
        Emit an if-then statement.
        """

        condition  = self.value_from_any(condition).cast_to(LLVM_Type.int(1))
        then       = self.function.append_basic_block("then")
        merge      = self.function.append_basic_block("merge")

        def decorator(emit):
            builder = self.builder

            builder.cbranch(condition.low, then, merge)
            builder.position_at_end(then)

            emit()

            if not self.block_terminated:
                builder.branch(merge)

            builder.position_at_end(merge)

        return decorator

    def if_else(self, condition):
        """
        Emit an if-then-else statement.
        """

        condition  = self.value_from_any(condition).cast_to(LLVM_Type.int(1))
        then       = self.function.append_basic_block("then")
        else_      = self.function.append_basic_block("else")

        def decorator(emit_branch):
            merge   = None
            builder = self.builder

            builder.cbranch(condition.low, then, else_)
            builder.position_at_end(then)

            emit_branch(True)

            if not self.block_terminated:
                if merge is None:
                    merge = self.function.append_basic_block("merge")

                builder.branch(merge)

            builder.position_at_end(else_)

            emit_branch(False)

            if not self.block_terminated:
                if merge is None:
                    merge = self.function.append_basic_block("merge")

                builder.branch(merge)

            if merge is not None:
                builder.position_at_end(merge)

        return decorator

    def for_(self, count):
        """
        Emit a simple for-style loop.
        """

        index_type = LLVM_Type.int(32)

        count = self.value_from_any(count)

        def decorator(emit_body):
            """
            Emit the IR for a particular loop body.
            """

            # prepare the loop structure
            builder  = self.builder
            start    = self.basic_block
            check    = self.function.append_basic_block("for_loop_check")
            flesh    = self.function.append_basic_block("for_loop_flesh")
            leave    = self.function.append_basic_block("for_loop_leave")

            # build the check block
            builder.branch(check)
            builder.position_at_end(check)

            this_index = builder.phi(index_type, "for_loop_index")

            this_index.add_incoming(LLVM_Constant.int(index_type, 0), start)

            builder.cbranch(
                builder.icmp(
                    llvm.core.ICMP_UGT,
                    count.low,
                    this_index,
                    ),
                flesh,
                leave,
                )

            # build the flesh block
            builder.position_at_end(flesh)

            emit_body(Value.from_low(this_index))

            this_index.add_incoming(
                builder.add(this_index, LLVM_Constant.int(index_type, 1)),
                builder.basic_block,
                )

            builder.branch(check)

            # wrap up the loop
            builder.position_at_end(leave)

        return decorator

    def select(self, boolean, if_true, if_false):
        """
        Conditionally return one of two values.
        """

        return \
            self.value_from_any(
                self.builder.select(
                    self.value_from_any(boolean)._value,
                    self.value_from_any(if_true)._value,
                    self.value_from_any(if_false)._value,
                    ),
                )

    def random(self):
        """
        Emit a PRNG invocation.
        """

        from qy.support import emit_random_real_unit

        return emit_random_real_unit(self)

    def random_int(self, upper, width = 32):
        """
        Emit a PRNG invocation.
        """

        from qy.support import emit_random_int

        return emit_random_int(self, upper, width)

    def log(self, value):
        """
        Emit a natural log computation.
        """

        log    = Function.intrinsic(llvm.core.INTR_LOG, [float])
        result = log(value)

        if self._test_for_nan:
            self.assert_(~result.is_nan, "result of log(%s) is not a number", value)

        return result

    def log1p(self, value):
        """
        Emit a natural log computation.
        """

        log1p = Function.named("log1p", float, [float])

        log1p._value.add_attribute(llvm.core.ATTR_NO_UNWIND)
        log1p._value.add_attribute(llvm.core.ATTR_READONLY)

        result = log1p(value)

        if self._test_for_nan:
            self.assert_(~result.is_nan, "result of log1p(%s) is not a number", value)

        return result

    def exp(self, value):
        """
        Emit a natural exponentiation.
        """

        exp    = Function.intrinsic(llvm.core.INTR_EXP, [float])
        result = exp(value)

        if self._test_for_nan:
            self.assert_(~result.is_nan, "result of exp(%s) is not a number", value)

        return result

    __whatever = []

    def python(self, *arguments):
        """
        Emit a call to a Python callable.
        """

        def decorator(callable_):
            """
            Emit a call to an arbitrary Python object.
            """

            # XXX properly associate a destructor with the module, etc

            Qy.__whatever += [callable_]

            from qy import constant_pointer_to

            Object(constant_pointer_to(callable_, self.object_ptr_type))(*arguments)

        return decorator

    def py_import(self, name):
        """
        Import a Python module.
        """

        object_ptr_type = self.module.get_type_named("PyObjectPtr")
        import_         = Function.named("PyImport_ImportModule", object_ptr_type, [LLVM_Type.pointer(LLVM_Type.int(8))])

        # XXX error handling

        return Object(import_(self.string_literal(name))._value)

    @contextmanager
    def py_scope(self):
        """
        Define a Python object lifetime scope.
        """

        yield ObjectScope()

    def py_tuple(self, *values):
        """
        Build a Python tuple from Qy values.
        """

        tuple_new      = Function.named("PyTuple_New", object_ptr_type, [ctypes.c_int])
        tuple_set_item = \
            Function.named(
                "PyTuple_SetItem",
                ctypes.c_int,
                [object_ptr_type, ctypes.c_size_t, object_ptr_type],
                )

        values_tuple = tuple_new(len(values))

        for (i, value) in enumerate(values):
            if value.type_ == self.object_ptr_type:
                self.py_inc_ref(value)

            tuple_set_item(values_tuple, i, value.to_python())

        return values_tuple

    def py_inc_ref(self, value):
        """
        Decrement the refcount of a Python object.
        """

        inc_ref = Function.named("Py_IncRef", LLVM_Type.void(), [object_ptr_type])

        inc_ref(value)

    def py_dec_ref(self, value):
        """
        Decrement the refcount of a Python object.
        """

        dec_ref = Function.named("Py_DecRef", LLVM_Type.void(), [object_ptr_type])

        dec_ref(value)

    def py_print(self, value):
        """
        Print a Python string via sys.stdout.
        """

        if isinstance(value, str):
            value = Object.from_string(value)
        elif value.type_ != self.object_ptr_type:
            raise TypeError("py_print() expects a str or object pointer argument")

        with self.py_scope():
            self.py_import("sys").get("stdout").get("write")(value)

    def py_printf(self, format_, *arguments):
        """
        Print arguments via to-Python conversion.
        """

        arguments       = map(self.value_from_any, arguments)
        object_ptr_type = self.object_ptr_type
        py_format       = Function.named("PyString_Format", object_ptr_type, [object_ptr_type] * 2)
        py_from_string  = Function.named("PyString_FromString", object_ptr_type, [LLVM_Type.pointer(LLVM_Type.int(8))])

        @Function.define(LLVM_Type.void(), [a.type_ for a in arguments])
        def py_printf(*inner_arguments):
            """
            Emit the body of the generated print function.
            """

            # build the output string
            format_object    = py_from_string(self.string_literal(format_))
            arguments_object = qy.py_tuple(*inner_arguments)
            output_object    = py_format(format_object, arguments_object)

            self.py_dec_ref(format_object)
            self.py_dec_ref(arguments_object)
            self.py_check_null(output_object)

            # write it to the standard output stream
            self.py_print(output_object)
            self.py_dec_ref(output_object)
            self.return_()

        py_printf(*arguments)

    def py_check_null(self, value):
        """
        Bail if a value is null.
        """

        from ctypes import c_int

        @qy.if_(value == 0)
        def _():
            longjmp = \
                Function.named(
                    "longjmp",
                    LLVM_Type.void(),
                    [LLVM_Type.pointer(LLVM_Type.int(8)), c_int],
                    )
            context = self.module.get_global_variable_named("main_context")

            longjmp._value.add_attribute(llvm.core.ATTR_NO_RETURN)

            longjmp(context, 1)

    def heap_allocate(self, type_, count = 1):
        """
        Stack-allocate and return a value.
        """

        from qy import size_of_type

        type_  = self.type_from_any(type_)
        malloc = Function.named("malloc", LLVM_Type.pointer(LLVM_Type.int(8)), [long])
        bytes_ = (self.value_from_any(count) * size_of_type(type_)).cast_to(long)

        return malloc(bytes_).cast_to(LLVM_Type.pointer(type_))

    def stack_allocate(self, type_, initial = None, name = ""):
        """
        Stack-allocate and return a value.
        """

        allocated = Value.from_low(self.builder.alloca(self.type_from_any(type_), name))

        if initial is not None:
            self.value_from_any(initial).store(allocated)

        return allocated

    def assert_(self, boolean, message = "false assertion", *arguments):
        """
        Assert a fact; bails out of the module if false.
        """

        from traceback import extract_stack

        boolean        = self.value_from_any(boolean).cast_to(LLVM_Type.int(1))
        emission_stack = extract_stack()[:-1]

        @self.if_(~boolean)
        def _():
            # XXX we can do this more simply (avoid the callable argument mangling, etc)
            @self.python(*arguments)
            def _(*pythonized):
                raise EmittedAssertionError(message % pythonized, emission_stack)

    def return_(self, value = None):
        """
        Emit a return statement.
        """

        if value is None:
            self.builder.ret_void()
        else:
            self.builder.ret(self.value_from_any(value)._value)

    @contextmanager
    def active(self):
        """
        Make a new language instance active in this context.
        """

        Qy._language_stack.append(self)

        yield self

        Qy._language_stack.pop()

    @contextmanager
    def this_builder(self, builder):
        """
        Temporarily alter the active builder.
        """

        self._builder_stack.append(builder)

        yield builder

        self._builder_stack.pop()

    @property
    def main(self):
        """
        Return the module entry point.
        """

        return self.module.get_function_named("main")

    @property
    def builder(self):
        """
        Return the current IR builder.
        """

        return self._builder_stack[-1]

    @property
    def basic_block(self):
        """
        Return the current basic block.
        """

        return self.builder.basic_block

    @property
    def function(self):
        """
        Return the current function.
        """

        return self.basic_block.function

    @property
    def module(self):
        """
        Return the current module.
        """

        return self._module

    @property
    def block_terminated(self):
        """
        Does the current basic block end with a terminator?
        """

        return                                                  \
            self.basic_block.instructions                       \
            and self.basic_block.instructions[-1].is_terminator

    @property
    def test_for_nan(self):
        """
        Is NaN testing enabled?
        """

        return self._test_for_nan

    @test_for_nan.setter
    def test_for_nan(self, test_for_nan):
        """
        Is NaN testing enabled?
        """

        self._test_for_nan = test_for_nan

    @property
    def object_ptr_type(self):
        """
        Return the PyObject* type.
        """

        return self.module.get_type_named("PyObjectPtr")

    @staticmethod
    def get_active():
        """
        Get the currently-active language instance.
        """

        return Qy._language_stack[-1]

class Value(object):
    """
    Value in the wrapper language.
    """

    def __init__(self, value):
        """
        Initialize.
        """

        if not isinstance(value, LLVM_Value):
            raise TypeError("Value constructor requires an llvm.core.Value")
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

        return Qy.get_active().builder.store(self._value, pointer._value)

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
        elif isinstance(value, LLVM_Value):
            return Value.from_low(value)
        elif isinstance(value, int):
            return \
                Value.from_low(
                    LLVM_Constant.int(
                        LLVM_Type.int(numpy.dtype(int).itemsize * 8),
                        int(value),
                        ),
                    )
        elif isinstance(value, long):
            return \
                Value.from_low(
                    LLVM_Constant.int(
                        LLVM_Type.int(numpy.dtype(long).itemsize * 8),
                        long(value),
                        ),
                    )
        elif isinstance(value, float):
            return \
                Value.from_low(
                    LLVM_Constant.real(LLVM_Type.double(), value),
                    )
        elif isinstance(value, bool):
            return Value.from_low(LLVM_Constant.int(LLVM_Type.int(1), int(value)))
        else:
            raise TypeError("cannot build value from \"%s\" instance" % type(value))

    @staticmethod
    def from_low(value):
        """
        Build a Qy value from an LLVM value.
        """

        # sanity
        if not isinstance(value, LLVM_Value):
            raise TypeError("value is not an LLVM value")

        # generate an appropriate value type
        if value.type.kind == llvm.core.TYPE_INTEGER:
            return IntegerValue(value)
        elif value.type.kind == llvm.core.TYPE_DOUBLE:
            return RealValue(value)
        elif value.type.kind == llvm.core.TYPE_POINTER:
            return PointerValue(value)
        else:
            return Value(value)

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

class IntegerValue(Value):
    """
    Integer value in the wrapper language.
    """

    def __invert__(self):
        """
        Return the result of bitwise inversion.
        """

        return get_qy().builder.xor(self._value, LLVM_Constant.int(self.type_, -1))

    def __eq__(self, other):
        """
        Return the result of an equality comparison.
        """

        return \
            Value.from_low(
                get_qy().builder.icmp(
                    llvm.core.ICMP_EQ,
                    self._value,
                    qy.value_from_any(other)._value,
                    ),
                )

    def __ge__(self, other):
        """
        Return the result of a greater-than comparison.
        """

        return \
            Value.from_low(
                get_qy().builder.icmp(
                    llvm.core.ICMP_SGE,
                    self._value,
                    qy.value_from_any(other).cast_to(self.type_)._value,
                    ),
                )

    def __le__(self, other):
        """
        Return the result of a less-than comparison.
        """

        return \
            Value.from_low(
                get_qy().builder.icmp(
                    llvm.core.ICMP_SLE,
                    self._value,
                    qy.value_from_any(other).cast_to(self.type_)._value,
                    ),
                )

    def __add__(self, other):
        """
        Return the result of an addition.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(get_qy().builder.add(self._value, other._value))

    def __sub__(self, other):
        """
        Return the result of a subtraction.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(get_qy().builder.sub(self._value, other._value))

    def __mul__(self, other):
        """
        Return the result of a multiplication.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(get_qy().builder.mul(self._value, other._value))

    def __div__(self, other):
        """
        Return the result of a division.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(get_qy().builder.sdiv(self._value, other._value))

    def __mod__(self, other):
        """
        Return the remainder of a division.

        Note that this operation performs C-style, not Python-style, modulo.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(get_qy().builder.srem(self._value, other._value))

    def __and__(self, other):
        """
        Return the result of a bitwise and.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(get_qy().builder.and_(self._value, other._value))

    def __xor__(self, other):
        """
        Return the result of a bitwise xor.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(get_qy().builder.xor(self._value, other._value))

    def __or__(self, other):
        """
        Return the result of a bitwise or.
        """

        other = qy.value_from_any(other).cast_to(self.type_)

        return IntegerValue(get_qy().builder.or_(self._value, other._value))

    def cast_to(self, type_, name = ""):
        """
        Cast this value to the specified type.
        """

        # XXX cleanly handle signedness somehow (explicit "signed" qy value?)

        type_     = qy.type_from_any(type_)
        low_value = None

        if type_.kind == llvm.core.TYPE_DOUBLE:
            low_value = get_qy().builder.sitofp(self._value, type_, name)
        elif type_.kind == llvm.core.TYPE_INTEGER:
            if self.type_.width == type_.width:
                low_value = self._value
            elif self.type_.width < type_.width:
                low_value = get_qy().builder.sext(self._value, type_, name)
            elif self.type_.width > type_.width:
                low_value = get_qy().builder.trunc(self._value, type_, name)

        if low_value is None:
            raise CoercionError(self.type_, type_)
        else:
            return Value.from_any(low_value)

    def to_python(self):
        """
        Emit conversion of this value to a Python object.
        """

        int_from_long = Function.named("PyInt_FromLong", object_ptr_type, [ctypes.c_long])

        return int_from_long(self._value)

class RealValue(Value):
    """
    Integer value in the wrapper language.
    """

    def __eq__(self, other):
        """
        Return the result of an equality comparison.
        """

        return \
            Value.from_low(
                get_qy().builder.fcmp(
                    llvm.core.FCMP_OEQ,
                    self._value,
                    qy.value_from_any(other)._value,
                    ),
                )

    def __gt__(self, other):
        """
        Return the result of a greater-than comparison.
        """

        return \
            Value.from_low(
                get_qy().builder.fcmp(
                    llvm.core.FCMP_OGT,
                    self._value,
                    qy.value_from_any(other).cast_to(self.type_)._value,
                    ),
                )

    def __ge__(self, other):
        """
        Return the result of a greater-than-or-equal comparison.
        """

        return \
            Value.from_low(
                get_qy().builder.fcmp(
                    llvm.core.FCMP_OGE,
                    self._value,
                    qy.value_from_any(other).cast_to(self.type_)._value,
                    ),
                )

    def __lt__(self, other):
        """
        Return the result of a less-than comparison.
        """

        return \
            Value.from_low(
                get_qy().builder.fcmp(
                    llvm.core.FCMP_OLT,
                    self._value,
                    qy.value_from_any(other).cast_to(self.type_)._value,
                    ),
                )

    def __le__(self, other):
        """
        Return the result of a less-than-or-equal comparison.
        """

        return \
            Value.from_low(
                get_qy().builder.fcmp(
                    llvm.core.FCMP_OLE,
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
        value = RealValue(get_qy().builder.fadd(self._value, other._value))

        if get_qy().test_for_nan:
            qy.assert_(~value.is_nan, "result of %s + %s is not a number", other, self)

        return value

    def __sub__(self, other):
        """
        Return the result of a subtraction.
        """

        other = qy.value_from_any(other).cast_to(self.type_)
        value = RealValue(get_qy().builder.fsub(self._value, other._value))

        if get_qy().test_for_nan:
            qy.assert_(~value.is_nan, "result of %s - %s is not a number", other, self)

        return value

    def __mul__(self, other):
        """
        Return the result of a multiplication.
        """

        other = qy.value_from_any(other).cast_to(self.type_)
        value = RealValue(get_qy().builder.fmul(self._value, other._value))

        if get_qy().test_for_nan:
            qy.assert_(~value.is_nan, "result of %s * %s is not a number", other, self)

        return value

    def __div__(self, other):
        """
        Return the result of a division.
        """

        other = qy.value_from_any(other).cast_to(self.type_)
        value = RealValue(get_qy().builder.fdiv(self._value, other._value))

        if get_qy().test_for_nan:
            qy.assert_(~value.is_nan, "result of %s / %s is not a number", other, self)

        return value

    @property
    def is_nan(self):
        """
        Test for nan.
        """

        return \
            Value.from_low(
                get_qy().builder.fcmp(
                    llvm.core.FCMP_UNO,
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

        if type_.kind == llvm.core.TYPE_DOUBLE:
            if self.type_.kind == llvm.core.TYPE_DOUBLE:
                low_value = self._value
        if type_.kind == llvm.core.TYPE_INTEGER:
            low_value = get_qy().builder.fptosi(self._value, type_, name)

        if low_value is None:
            raise CoercionError(self.type_, type_)
        else:
            return Value.from_low(low_value)

    def to_python(self):
        """
        Emit conversion of this value to a Python object.
        """

        float_from_double = Function.named("PyFloat_FromDouble", object_ptr_type, [float])

        return float_from_double(self._value)

class PointerValue(Value):
    """
    Pointer value in the wrapper language.
    """

    def __eq__(self, other):
        """
        Return the result of an equality comparison.
        """

        return \
            Value.from_low(
                get_qy().builder.icmp(
                    llvm.core.ICMP_EQ,
                    get_qy().builder.ptrtoint(self._value, iptr_type),
                    qy.value_from_any(other).cast_to(iptr_type)._value,
                    ),
                )

    def load(self, name = ""):
        """
        Load the value pointed to by this pointer.
        """

        return \
            Value.from_low(
                get_qy().builder.load(self._value, name = name),
                )

    def gep(self, *indices):
        """
        Return a pointer to a component.
        """

        return \
            Value.from_low(
                get_qy().builder.gep(
                    self._value,
                    [Value.from_any(i)._value for i in indices],
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

        if type_.kind == llvm.core.TYPE_POINTER:
            low_value = get_qy().builder.bitcast(self._value, type_, name)
        elif type_.kind == llvm.core.TYPE_INTEGER:
            if type_.width == iptr_type.width:
                low_value = get_qy().builder.ptrtoint(self._value, type_, name)

        if low_value is None:
            raise CoercionError(self.type_, type_)
        else:
            return Value.from_any(low_value)

class StructValue(Value):
    """
    Struct value in the wrapper language.
    """

class Function(Value):
    """
    Function in the wrapper language.
    """

    def __call__(self, *arguments):
        """
        Emit IR for a function call.
        """

        # sanity
        if len(arguments) != len(self.argument_types):
            raise TypeError(
                "function %s expects %i arguments but received %i" % (
                    self._value.name,
                    len(self.argument_types),
                    len(arguments),
                    ),
                )

        # emit the call
        arguments = map(qy.value_from_any, arguments)
        coerced   = [v.cast_to(a) for (v, a) in zip(arguments, self.argument_types)]

        return \
            Value.from_low(
                get_qy().builder.call(
                    self._value,
                    [c.low for c in coerced],
                    ),
                )

    @property
    def argument_values(self):
        """
        Return the function argument values.

        Meaningful only inside the body of this function.
        """

        return map(qy.value_from_any, self._value.args)

    @property
    def argument_types(self):
        """
        Return the function argument values.

        Meaningful only inside the body of this function.
        """

        if self.type_.kind == llvm.core.TYPE_POINTER:
            return self.type_.pointee.args
        else:
            return self.type_.args

    @staticmethod
    def named(name, return_type = LLVM_Type.void(), argument_types = ()):
        """
        Look up or create a named function.
        """

        type_ = \
            LLVM_Type.function(
                qy.type_from_any(return_type),
                map(qy.type_from_any, argument_types),
                )

        return Function(Qy.get_active().module.get_or_insert_function(type_, name))

    @staticmethod
    def get_named(name):
        """
        Look up a named function.
        """

        return Function(Qy.get_active().module.get_function_named(name))

    @staticmethod
    def new_named(name, return_type = LLVM_Type.void(), argument_types = (), internal = True):
        """
        Create a named function.
        """

        type_ = \
            LLVM_Type.function(
                qy.type_from_any(return_type),
                map(qy.type_from_any, argument_types),
                )
        function = Qy.get_active().module.add_function(type_, name)

        if internal:
            function.linkage = llvm.core.LINKAGE_INTERNAL

        return Function(function)

    @staticmethod
    def define(return_type = LLVM_Type.void(), argument_types = (), name = None, internal = True):
        """
        Look up or create a named function.
        """

        def decorator(emit):
            """
            Emit the body of the function.
            """

            if name is None:
                if emit.__name__ == "_":
                    function_name = "function"
                else:
                    function_name = emit.__name__
            else:
                function_name = name

            function = Function.new_named(function_name, return_type, argument_types, internal = internal)

            entry = function._value.append_basic_block("entry")

            with qy.this_builder(LLVM_Builder.new(entry)) as builder:
                emit(*function.argument_values)

            return function

        return decorator

    @staticmethod
    def pointed(address, return_type, argument_types):
        """
        Return a function from a function pointer.
        """

        type_ = \
            LLVM_Type.function(
                qy.type_from_any(return_type),
                map(qy.type_from_any, argument_types),
                )

        return Function(LLVM_Constant.int(iptr_type, address).inttoptr(LLVM_Type.pointer(type_)))

    @staticmethod
    def intrinsic(intrinsic_id, qualifiers = ()):
        """
        Return an intrinsic function.
        """

        qualifiers = map(qy.type_from_any, qualifiers)

        return Function(LLVM_Function.intrinsic(Qy.get_active().module, intrinsic_id, qualifiers))

class Object(PointerValue):
    """
    Interact with Python objects from Qy.
    """

    def __call__(self, *arguments):
        """
        Emit a Python call.
        """

        arguments = map(qy.value_from_any, arguments)

        @Function.define(
            LLVM_Type.void(),
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
                [object_ptr_type, LLVM_Type.pointer(LLVM_Type.int(8))],
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
                [LLVM_Type.pointer(LLVM_Type.int(8))],
                )

        return Object(py_from_string(qy.string_literal(string))._value)

class ObjectScope(object):
    """
    Define the scope of allocated Python objects.
    """

    # XXX unimplemented; we're leaking Python objects

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

