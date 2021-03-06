"""
@author: Bryan Silverthorn <bcs@cargo-cult.org>
"""

import ctypes
import numpy
import qy
import qy.llvm as llvm

def semicast(*arrays):
    """
    Broadcast compatible ndarray shape prefixes.
    """

    # establish the final prefix shape
    pre_ndim    = max(len(a.shape[:i]) for (a, i) in arrays)
    pre_padding = [(1,) * (pre_ndim - len(a.shape[:i])) for (a, i) in arrays]
    pre_shape   = tuple(map(max, *(p + a.shape[:i] for ((a, i), p) in zip(arrays, pre_padding))))

    # broadcast the arrays
    from numpy.lib.stride_tricks import as_strided

    casts = []

    for ((a, i), p) in zip(arrays, pre_padding):
        if i is None:
            i = len(a.shape)

        for (c, d) in zip(pre_shape[len(p):], a.shape[:i]):
            if c != d and d != 1:
                raise ValueError("array shapes incompatible for semicast")

        strides  = (0,) * len(p) + tuple(0 if d == 1 else s for (d, s) in zip(a.shape, a.strides))
        casts   += [as_strided(a, pre_shape + a.shape[i:], strides)]

    # repair dtypes (broken by as_strided)
    for ((a, _), cast) in zip(arrays, casts):
        cast.dtype = a.dtype

    # done
    return (pre_shape, casts)

class StridedArrays(object):
    """
    Emit IR for manipulating strided arrays of compatible shape.
    """

    def __init__(self, arrays):
        """
        Initialize.
        """

        self._arrays = dict(arrays)

    def at_all(self, *indices):
        """
        Emit IR to return subarrays at a particular location.
        """

        return StridedArrays((k, v.at(*indices)) for (k, v) in self._arrays.items())

    def loop_all(self, axes = None):
        """
        Iterate over strided arrays.
        """

        # argument sanity
        shape = None

        for array in self._arrays.values():
            if shape is None:
                if axes is None:
                    axes = len(array.shape)

                shape = array.shape[:axes]
            elif array.shape[:axes] != shape:
                raise ValueError("incompatible array shape")

        def decorator(emit_inner):
            """
            Emit IR for a particular inner loop body.
            """

            def emit_for_axis(d, indices):
                """
                Build one level of the array loop.
                """

                if d == axes:
                    emit_inner(self.at_all(*indices))
                elif shape[d] > 1:
                    @qy.for_(shape[d])
                    def _(index):
                        emit_for_axis(d + 1, indices + [index])
                else:
                    emit_for_axis(d + 1, indices + [0])

            emit_for_axis(0, [])

        return decorator

    @property
    def arrays(self):
        """
        Return the inner arrays.
        """

        return self._arrays

    @staticmethod
    def from_numpy(ndarrays):
        """
        Build from a dictionary of ndarrays.
        """

        pairs = ((k, StridedArray.from_numpy(v)) for (k, v) in ndarrays.items())

        return StridedArrays(dict(pairs))

def get_strided_type(element_type, shape, strides):
    """
    Build an LLVM type to represent a strided array's structure.
    """

    if shape:
        (inner_type, inner_size) = get_strided_type(element_type, shape[1:], strides[1:])

        if strides[0] == 0:
            return (inner_type, inner_size)
        else:
            if strides[0] < inner_size:
                raise ValueError("array stride too small")
            else:
                return (
                    llvm.Type.array(
                        llvm.Type.packed_struct([
                            inner_type,
                            llvm.Type.array(llvm.Type.int(8), strides[0] - inner_size),
                            ]),
                        shape[0],
                        ),
                    shape[0] * strides[0],
                    )
    else:
        from qy import size_of_type

        return (element_type, size_of_type(element_type))

class StridedArray(object):
    """
    Emit IR for interaction with a strided array.
    """

    def __init__(self, strided_data, shape, strides, element_type):
        """
        Initialize.
        """

        self._strided_data = strided_data
        self._shape        = shape
        self._strides      = strides
        self._element_type = element_type

    def at(self, *indices):
        """
        Emit IR to retrieve a subarray at a particular location.
        """

        # sanity
        if len(indices) > len(self._shape):
            raise ValueError("too many indices")

        # build up getelementptr indices
        offsets = []

        for (index, stride) in zip(indices, self._strides):
            if stride > 0:
                offsets += [0, index]

        offsets += [0]

        # index into the array
        return \
            StridedArray(
                self._strided_data.gep(*offsets),
                self._shape[len(indices):],
                self._strides[len(indices):],
                self._element_type,
                )

    def envelop(self, axes = 1):
        """
        Add preceding unit dimensions.
        """

        return \
            StridedArray(
                self._strided_data,
                [1] + self._shape,
                [0] + self._strides,
                self._element_type,
                )

    def extract(self, *indices):
        """
        Build an array over an aggregate member.
        """

        # XXX need to include axes which may have emerged
        # XXX need some general clarification of the StridedArray model?

        simple_data = self._strided_data.cast_to(llvm.Type.pointer(self._element_type))
        inner_data  = simple_data.gep(*indices)

        return StridedArray.from_raw(inner_data, self._shape, self._strides)

    def using(self, strided_data):
        """
        Return an equivalent array using a different data pointer.
        """

        return StridedArray(strided_data, self._shape, self._strides, self._element_type)

    @property
    def data(self):
        """
        The strided pointer associated with this array.
        """

        return self._strided_data

    @property
    def shape(self):
        """
        The shape of this array.
        """

        return self._shape

    @property
    def strides(self):
        """
        The strides of this array.
        """

        return self._strides

    @staticmethod
    def from_raw(data, shape, strides = None):
        """
        Build an array from a typical data pointer.

        @param data    : Pointer value (with element-pointer type) to array data.
        @param shape   : Tuple of dimension sizes (Python integers).
        @param strides : Tuple of dimension strides (Python integers).
        """

        shape = map(int, shape)

        if strides is None:
            from qy import size_of_type

            strides   = []
            axis_size = size_of_type(data.type_.pointee)

            for d in reversed(shape):
                strides   += [axis_size]
                axis_size *= d

            strides = list(reversed(strides))
        else:
            strides = map(int, strides)

        (strided_type, _) = get_strided_type(data.type_.pointee, shape, strides)
        strided_data      = data.cast_to(llvm.Type.pointer(strided_type))

        return StridedArray(strided_data, shape, strides, data.type_.pointee)

    @staticmethod
    def from_numpy(ndarray):
        """
        Build an array from a particular numpy array.
        """

        # XXX maintain reference to array in module; decref in destructor

        from qy import type_from_dtype

        type_         = type_from_dtype(ndarray.dtype)
        (location, _) = ndarray.__array_interface__["data"]
        data          = llvm.Constant.int(iptr_type, location).inttoptr(llvm.Type.pointer(type_))

        return StridedArray.from_raw(qy.value_from_any(data), ndarray.shape, ndarray.strides)

    @staticmethod
    def from_typed_pointer(data):
        """
        Build an array from a typical array pointer.
        """

        if data.type_.kind != llvm.core.TYPE_POINTER:
            raise TypeError("pointer value required")
        elif data.type_.kind != llvm.core.TYPE_ARRAY:
            return StridedArray(data, (), (), data.type_)
        else:
            raise NotImplementedError()

    @staticmethod
    def heap_allocated(type_, shape):
        """
        Heap-allocate and return a (contiguous) array.
        """

        data = qy.heap_allocate(type_, numpy.product(shape))

        return StridedArray.from_raw(data, shape)

