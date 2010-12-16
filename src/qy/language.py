"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

__all__ = [
    "object_type",
    "object_ptr_type",
    "EmittedAssertionError",
    "get",
    "Qy",
    ]

import ctypes
import contextlib
import numpy
import qy
import qy.llvm as llvm

object_type     = llvm.Type.struct([])
object_ptr_type = llvm.Type.pointer(object_type)

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

def get():
    """
    Return the currently-active Qy language instance.
    """

    return Qy.get_active()

class Qy(object):
    """
    The Qy language configuration and language statements.
    """

    _language_stack = []

    def __init__(self, module = None, test_for_nan = False):
        """
        Initialize.
        """

        # members
        if module is None:
            module = llvm.Module.new("qy")

        self._module        = module
        self._test_for_nan  = test_for_nan
        self._literals      = {}
        self._builder_stack = []
        self._break_stack   = []

        # make Python-support declarations
        self._module.add_type_name("PyObjectPtr", llvm.Type.pointer(llvm.Type.struct([])))

        with self.active():
            # add a main
            main_body = qy.Function.new_named("main_body")

            @qy.Function.define(internal = False)
            def main():
                """
                The true entry point.
                """

                # initialize the Python runtime (matters only for certain test scenarios)
                qy.Function.named("Py_Initialize")()

                # prepare for exception handling
                from qy.support import size_of_jmp_buf

                context_type = llvm.Type.array(llvm.Type.int(8), size_of_jmp_buf())
                context      = llvm.GlobalVariable.new(self._module, context_type, "main_context")
                setjmp       = qy.Function.named("setjmp", int, [llvm.Type.pointer(llvm.Type.int(8))])

                context.linkage     = llvm.LINKAGE_INTERNAL
                context.initializer = llvm.Constant.null(context_type)

                self.if_(setjmp(context) == 0)(main_body)
                self.return_()

        # prepare for user code
        body_entry = main_body._value.append_basic_block("entry")

        self._builder_stack.append(llvm.Builder.new(body_entry))

    def value_from_any(self, value):
        """
        Return a wrapping value.
        """

        from qy import Value

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
        elif isinstance(some_type, llvm.Type):
            return some_type
        elif some_type in ctype_integer_types:
            return llvm.Type.int(sizeof(some_type) * 8)
        else:
            raise TypeError("cannot build type from \"%s\" instance" % type(some_type))

    def string_literal(self, string):
        """
        Define a new string literal.
        """

        from qy import Value

        if string not in self._literals:
            name  = "literal%i" % len(self._literals)
            value = \
                Value.from_low(
                    llvm.GlobalVariable.new(
                        self.module,
                        llvm.Type.array(llvm.Type.int(8), len(string) + 1),
                        name,
                        ),
                    )

            value._value.linkage     = llvm.LINKAGE_INTERNAL
            value._value.initializer = llvm.Constant.stringz(string)

            self._literals[string] = value

            return value
        else:
            return self._literals[string]

    def if_(self, condition):
        """
        Emit an if-then statement.
        """

        condition  = self.value_from_any(condition).cast_to(llvm.Type.int(1))
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

        condition  = self.value_from_any(condition).cast_to(llvm.Type.int(1))
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

        index_type = llvm.Type.int(32)

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

            this_index.add_incoming(llvm.Constant.int(index_type, 0), start)

            builder.cbranch(
                builder.icmp(
                    llvm.ICMP_UGT,
                    count.low,
                    this_index,
                    ),
                flesh,
                leave,
                )

            # build the flesh block
            from qy import Value

            builder.position_at_end(flesh)

            self._break_stack.append(leave)

            emit_body(Value.from_low(this_index))

            self._break_stack.pop()

            this_index.add_incoming(
                builder.add(this_index, llvm.Constant.int(index_type, 1)),
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

        log    = qy.Function.intrinsic(llvm.INTR_LOG, [float])
        result = log(value)

        if self._test_for_nan:
            self.assert_(~result.is_nan, "result of log(%s) is not a number", value)

        return result

    def log1p(self, value):
        """
        Emit a natural log computation.
        """

        log1p = qy.Function.named("log1p", float, [float])

        log1p._value.add_attribute(llvm.ATTR_NO_UNWIND)
        log1p._value.add_attribute(llvm.ATTR_READONLY)

        result = log1p(value)

        if self._test_for_nan:
            self.assert_(~result.is_nan, "result of log1p(%s) is not a number", value)

        return result

    def exp(self, value):
        """
        Emit a natural exponentiation.
        """

        exp    = qy.Function.intrinsic(llvm.INTR_EXP, [float])
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

            from qy import (
                Object,
                constant_pointer_to,
                )

            Object(constant_pointer_to(callable_, self.object_ptr_type))(*arguments)

        return decorator

    def py_import(self, name):
        """
        Import a Python module.
        """

        object_ptr_type = self.module.get_type_named("PyObjectPtr")
        import_         = qy.Function.named("PyImport_ImportModule", object_ptr_type, [llvm.Type.pointer(llvm.Type.int(8))])

        # XXX error handling

        return Object(import_(self.string_literal(name))._value)

    @contextlib.contextmanager
    def py_scope(self):
        """
        Define a Python object lifetime scope.
        """

        yield ObjectScope()

    def py_tuple(self, *values):
        """
        Build a Python tuple from Qy values.
        """

        tuple_new      = qy.Function.named("PyTuple_New", object_ptr_type, [ctypes.c_int])
        tuple_set_item = \
            qy.Function.named(
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

        inc_ref = qy.Function.named("Py_IncRef", llvm.Type.void(), [object_ptr_type])

        inc_ref(value)

    def py_dec_ref(self, value):
        """
        Decrement the refcount of a Python object.
        """

        dec_ref = qy.Function.named("Py_DecRef", llvm.Type.void(), [object_ptr_type])

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
        py_format       = qy.Function.named("PyString_Format", object_ptr_type, [object_ptr_type] * 2)
        py_from_string  = qy.Function.named("PyString_FromString", object_ptr_type, [llvm.Type.pointer(llvm.Type.int(8))])

        @qy.Function.define(llvm.Type.void(), [a.type_ for a in arguments])
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
                qy.Function.named(
                    "longjmp",
                    llvm.Type.void(),
                    [llvm.Type.pointer(llvm.Type.int(8)), c_int],
                    )
            context = self.module.get_global_variable_named("main_context")

            longjmp._value.add_attribute(llvm.ATTR_NO_RETURN)

            longjmp(context, 1)

    def heap_allocate(self, type_, count = 1):
        """
        Heap-allocate and return a value.
        """

        # emit the allocation
        from qy import size_of_type

        type_  = self.type_from_any(type_)
        malloc = qy.Function.named("malloc", llvm.Type.pointer(llvm.Type.int(8)), [long])
        bytes_ = (self.value_from_any(count) * size_of_type(type_)).cast_to(long)

        return malloc(bytes_).cast_to(llvm.Type.pointer(type_))

    def heap_free(self, pointer):
        """
        Free a heap-allocated value.
        """

        u8p_type = llvm.Type.pointer(llvm.Type.int(8))
        free     = qy.Function.named("free", llvm.Type.void(), [u8p_type])

        free(pointer.cast_to(u8p_type))

    def stack_allocate(self, type_, initial = None, name = ""):
        """
        Stack-allocate and return a value.
        """

        from qy import Value

        allocated = Value.from_low(self.builder.alloca(self.type_from_any(type_), name))

        if initial is not None:
            self.value_from_any(initial).store(allocated)

        return allocated

    def assert_(self, boolean, message = "false assertion", *arguments):
        """
        Assert a fact; bails out of the module if false.
        """

        from traceback import extract_stack

        boolean        = self.value_from_any(boolean).cast_to(llvm.Type.int(1))
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

    def break_(self):
        """
        Emit an exit from the innermost loop.
        """

        self.builder.branch(self._break_stack[-1])

    @contextlib.contextmanager
    def active(self):
        """
        Make a new language instance active in this context.
        """

        Qy._language_stack.append(self)

        yield self

        Qy._language_stack.pop()

    @contextlib.contextmanager
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

