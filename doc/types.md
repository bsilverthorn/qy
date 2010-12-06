The Qy type system
==================

Goals
-----

The Qy type system should avoid straying too far from the LLVM type system. The
function from Qy types to LLVM types isn't strictly one-to-one (eg, both signed
and unsigned Qy integers map to the single LLVM integer type) or onto (eg, no
Qy type maps to an LLVM vector type), but every Qy type corresponds to exactly
one LLVM type, and no two distinct Qy types correspond to the same LLVM type.

