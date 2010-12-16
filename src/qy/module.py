"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

import ctypes
import contextlib
import numpy
import qy.llvm as llvm

iptr_type = llvm.Type.int(ctypes.sizeof(ctypes.c_void_p) * 8)

def constant_pointer(address, type_):
    """
    Return an LLVM pointer constant from an address.
    """

    return llvm.Constant.int(iptr_type, address).inttoptr(type_)

def constant_pointer_to(object_, type_):
    """
    Return an LLVM pointer constant to a Python object.
    """

    # XXX do this without assuming id behavior (using ctypes?)

    return constant_pointer(id(object_), type_)

def emit_and_execute(module_name = "", optimize = True):
    """
    Prepare for, emit, and run some LLVM IR.
    """

    from qy import Qy

    def decorator(emit):
        """
        Build an LLVM module, then execute it.
        """

        # construct the module
        with Qy().active() as this:
            emit()

            this.return_()

        module = this.module

        module.verify()

        # optimize it
        engine = llvm.ExecutionEngine.new(module)

        #if optimize:
            #manager = llvm.PassManager.new()

            #manager.add(engine.target_data)

            #manager.add(llvm.passes.PASS_FUNCTION_INLINING)
            #manager.add(llvm.passes.PASS_PROMOTE_MEMORY_TO_REGISTER)
            #manager.add(llvm.passes.PASS_BASIC_ALIAS_ANALYSIS)
            #manager.add(llvm.passes.PASS_CONSTANT_PROPAGATION)
            #manager.add(llvm.passes.PASS_INSTRUCTION_COMBINING)
            #manager.add(llvm.passes.PASS_IND_VAR_SIMPLIFY)
            #manager.add(llvm.passes.PASS_GEP_SPLITTER)
            #manager.add(llvm.passes.PASS_LOOP_SIMPLIFY)
            #manager.add(llvm.passes.PASS_LICM)
            #manager.add(llvm.passes.PASS_LOOP_ROTATE)
            #manager.add(llvm.passes.PASS_LOOP_STRENGTH_REDUCE)
            #manager.add(llvm.passes.PASS_LOOP_UNROLL)
            #manager.add(llvm.passes.PASS_GVN)
            #manager.add(llvm.passes.PASS_DEAD_STORE_ELIMINATION)
            #manager.add(llvm.passes.PASS_DEAD_CODE_ELIMINATION)
            #manager.add(llvm.passes.PASS_CFG_SIMPLIFICATION)

            #manager.run(module)

        # execute it
        engine.run_function(this.main, [])

        qy.raise_if_set()

    return decorator

def type_from_struct_type(dtype):
    """
    Build an LLVM type matching a numpy struct dtype.
    """

    fields   = sorted(dtype.fields.values(), key = lambda (_, p): p)
    members  = []
    position = 0

    for (field_dtype, offset) in fields:
        if offset != position:
            raise NotImplementedError("no support for dtypes with nonstandard packing")
        else:
            members  += [type_from_dtype(field_dtype)]
            position += field_dtype.itemsize

    return llvm.Type.packed_struct(members)

def type_from_shaped_dtype(base, shape):
    """
    Build an LLVM type matching a shaped numpy dtype.
    """

    if shape:
        return llvm.Type.array(type_from_shaped_dtype(base, shape[1:]), shape[0])
    else:
        return type_from_dtype(base)

def type_from_dtype(dtype):
    """
    Build an LLVM type matching a numpy dtype.
    """

    if dtype.shape:
        return type_from_shaped_dtype(dtype.base, dtype.shape)
    elif numpy.issubdtype(dtype, numpy.integer):
        return llvm.Type.int(dtype.itemsize * 8)
    elif dtype == numpy.float64:
        return llvm.Type.double()
    elif dtype == numpy.float32:
        return llvm.Type.float()
    elif dtype.fields:
        return type_from_struct_type(dtype)
    else:
        raise ValueError("could not build an LLVM type for dtype %s" % dtype.descr)

def size_of_type(type_):
    """
    Return the size of an instance of a type, in bytes.
    """

    return dtype_from_type(type_).itemsize

def normalize_dtype(dtype):
    """
    Construct an equivalent normal-form dtype.

    Normal-form dtypes are guaranteed to satisfy, in particular, the property
    of "shape greediness": the dtype's base property, if non-None, refers to a
    type with empty shape.
    """

    if dtype.shape:
        normal_base = normalize_dtype(dtype.base)

        return numpy.dtype((normal_base.base, dtype.shape + normal_base.shape))
    else:
        return dtype

def dtype_from_integer_type(type_):
    """
    Build a numpy dtype from an LLVM integer type.
    """

    sizes = {
        8  : numpy.dtype(numpy.int8),
        16 : numpy.dtype(numpy.int16),
        32 : numpy.dtype(numpy.int32),
        64 : numpy.dtype(numpy.int64),
        }

    return sizes[type_.width]

def dtype_from_array_type(type_):
    """
    Build a numpy dtype from an LLVM array type.
    """

    raw_dtype = numpy.dtype((dtype_from_type(type_.element), (type_.count,)))

    return normalize_dtype(raw_dtype)

def dtype_from_struct_type(type_):
    """
    Build a numpy dtype from an LLVM struct type.
    """

    fields = [("f%i" % i, dtype_from_type(f)) for (i, f) in enumerate(type_.elements)]

    return numpy.dtype(fields)

def dtype_from_type(type_):
    """
    Build a numpy dtype from an LLVM type.
    """

    mapping = {
        llvm.TYPE_FLOAT   : (lambda _ : numpy.dtype(numpy.float32)),
        llvm.TYPE_DOUBLE  : (lambda _ : numpy.dtype(numpy.float64)),
        llvm.TYPE_INTEGER : dtype_from_integer_type,
        llvm.TYPE_STRUCT  : dtype_from_struct_type,
        llvm.TYPE_ARRAY   : dtype_from_array_type,
        }

    return mapping[type_.kind](type_)

