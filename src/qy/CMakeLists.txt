#
# build
#

add_cython_module(qy_support support)

target_link_libraries(qy_support)

#
# install
#

install(
    TARGETS
        qy_support
    DESTINATION lib/qy
    )
install(
    FILES
        __init__.py
        language.py
        lowloop.py
        module.py
        statements.py
        math.py
        llvm.py
    DESTINATION lib/qy
    )

#
# descend
#

add_subdirectory(values)
add_subdirectory(test)

