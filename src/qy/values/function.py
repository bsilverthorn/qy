"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

import qy
import qy.llvm as llvm

class Function(qy.Value):
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
            qy.Value.from_low(
                qy.get().builder.call(
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

        if self.type_.kind == llvm.TYPE_POINTER:
            return self.type_.pointee.args
        else:
            return self.type_.args

    @staticmethod
    def named(name, return_type = llvm.Type.void(), argument_types = ()):
        """
        Look up or create a named function.
        """

        type_ = \
            llvm.Type.function(
                qy.type_from_any(return_type),
                map(qy.type_from_any, argument_types),
                )

        return Function(qy.get().module.get_or_insert_function(type_, name))

    @staticmethod
    def get_named(name):
        """
        Look up a named function.
        """

        return Function(qy.get().module.get_function_named(name))

    @staticmethod
    def new_named(name, return_type = llvm.Type.void(), argument_types = (), internal = True):
        """
        Create a named function.
        """

        type_ = \
            llvm.Type.function(
                qy.type_from_any(return_type),
                map(qy.type_from_any, argument_types),
                )
        function = qy.get().module.add_function(type_, name)

        if internal:
            function.linkage = llvm.LINKAGE_INTERNAL

        return Function(function)

    @staticmethod
    def define(return_type = llvm.Type.void(), argument_types = (), name = None, internal = True):
        """
        Create a named function.
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

            with qy.this_builder(llvm.Builder.new(entry)) as builder:
                emit(*function.argument_values)

            return function

        return decorator
    
    @staticmethod
    def define_once(return_type = llvm.Type.void(), argument_types = (), name = None, internal = True):
        """
        Look up or create a named function.
        """

        def decorator(emit):
            """
            Look up or emit the function.
            """

            if name is None:
                if emit.__name__ == "_":
                    function_name = "function"
                else:
                    function_name = emit.__name__
            else:
                function_name = name

            if function_name in qy.get().module.global_variables:
                return Function.get_named(function_name)
            else:
                define_decorator =                       \
                    Function.define(
                        return_type    = return_type,
                        argument_types = argument_types,
                        name           = name,
                        internal       = internal,
                        )                                \

                return define_decorator(emit)

        return decorator

    @staticmethod
    def pointed(address, return_type, argument_types):
        """
        Return a function from a function pointer.
        """

        type_ = \
            llvm.Type.function(
                qy.type_from_any(return_type),
                map(qy.type_from_any, argument_types),
                )

        return Function(llvm.Constant.int(iptr_type, address).inttoptr(llvm.Type.pointer(type_)))

    @staticmethod
    def intrinsic(intrinsic_id, qualifiers = ()):
        """
        Return an intrinsic function.
        """

        qualifiers = map(qy.type_from_any, qualifiers)

        return Function(llvm.Function.intrinsic(qy.get().module, intrinsic_id, qualifiers))

