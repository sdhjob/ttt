configure_file(${CMAKE_CURRENT_SOURCE_DIR}/include/sou/chain/core_symbol.hpp.in ${CMAKE_CURRENT_BINARY_DIR}/include/sou/chain/core_symbol.hpp)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/genesis_state_root_key.cpp.in ${CMAKE_CURRENT_BINARY_DIR}/genesis_state_root_key.cpp)

file(GLOB HEADERS "include/sou/chain/*.hpp"
                  "include/sou/chain/webassembly/*.hpp"
                  "${CMAKE_CURRENT_BINARY_DIR}/include/sou/chain/core_symbol.hpp" )

if(APPLE AND UNIX)
   set(PLATFORM_TIMER_IMPL platform_timer_macos.cpp)
else()
   try_run(POSIX_TIMER_TEST_RUN_RESULT POSIX_TIMER_TEST_COMPILE_RESULT ${CMAKE_CURRENT_BINARY_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/platform_timer_posix_test.c)
   if(POSIX_TIMER_TEST_RUN_RESULT EQUAL 0)
      set(PLATFORM_TIMER_IMPL platform_timer_posix.cpp)
   else()
      set(PLATFORM_TIMER_IMPL platform_timer_asio_fallback.cpp)
   endif()
endif()

if("sou-vm-oc" IN_LIST SOU_WASM_RUNTIMES)
   set(CHAIN_SOUVMOC_SOURCES webassembly/sou-vm-oc/code_cache.cpp
                             webassembly/sou-vm-oc/executor.cpp
                             webassembly/sou-vm-oc/memory.cpp
                             webassembly/sou-vm-oc/intrinsic.cpp
                             webassembly/sou-vm-oc/LLVMJIT.cpp
                             webassembly/sou-vm-oc/LLVMEmitIR.cpp
                             webassembly/sou-vm-oc/compile_monitor.cpp
                             webassembly/sou-vm-oc/compile_trampoline.cpp
                             webassembly/sou-vm-oc/ipc_helpers.cpp
                             webassembly/sou-vm-oc/gs_seg_helpers.c
                             webassembly/sou-vm-oc.cpp)

   if(LLVM_VERSION VERSION_LESS 7.1 AND CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
      enable_language(ASM-LLVMWAR)
      list(APPEND CHAIN_SOUVMOC_SOURCES webassembly/sou-vm-oc/llvmWARshim.llvmwar)
   else()
      list(APPEND CHAIN_SOUVMOC_SOURCES webassembly/sou-vm-oc/llvmWARshim.cpp)
   endif()

   llvm_map_components_to_libnames(LLVM_LIBS support core passes mcjit native orcjit)
   include_directories(${LLVM_INCLUDE_DIRS})
   add_definitions(${LLVM_DEFINITIONS})

   option(SOUVMOC_ENABLE_DEVELOPER_OPTIONS "enable developer options for SOU VM OC" OFF)
endif()

if("sou-vm" IN_LIST SOU_WASM_RUNTIMES OR "sou-vm-jit" IN_LIST SOU_WASM_RUNTIMES)
   set(CHAIN_SOUVM_SOURCES "webassembly/sou-vm.cpp")
   set(CHAIN_SOUVM_LIBRARIES sou-vm)
endif()

## SORT .cpp by most likely to change / break compile
add_library( sou_chain
             merkle.cpp
             name.cpp
             transaction.cpp
             block.cpp
             block_header.cpp
             block_header_state.cpp
             block_state.cpp
             fork_database.cpp
             controller.cpp
             authorization_manager.cpp
             resource_limits.cpp
             block_log.cpp
             transaction_context.cpp
             sou_contract.cpp
             sou_contract_abi.cpp
             sou_contract_abi_bin.cpp
             chain_config.cpp
             chain_id_type.cpp
             genesis_state.cpp
             ${CMAKE_CURRENT_BINARY_DIR}/genesis_state_root_key.cpp

#             chain_config.cpp
#             block_trace.cpp
              wast_to_wasm.cpp
              wasm_interface.cpp
              wasm_sou_validation.cpp
              wasm_sou_injection.cpp
              apply_context.cpp
              abi_serializer.cpp
              asset.cpp
              snapshot.cpp

             webassembly/wabt.cpp
             ${CHAIN_SOUVMOC_SOURCES}
             ${CHAIN_SOUVM_SOURCES}

#             get_config.cpp
#
#             contracts/chain_initializer.cpp

             trace.cpp
             transaction_metadata.cpp
             protocol_state_object.cpp
             protocol_feature_activation.cpp
             protocol_feature_manager.cpp
             producer_schedule.cpp
             genesis_intrinsics.cpp
             whitelisted_intrinsics.cpp
             thread_utils.cpp
             platform_timer_accuracy.cpp
             ${PLATFORM_TIMER_IMPL}
             ${HEADERS}
             )

target_link_libraries( sou_chain fc chainbase Logging IR WAST WASM Runtime
                       softfloat builtins wabt ${CHAIN_SOUVM_LIBRARIES} ${LLVM_LIBS}
                     )
target_include_directories( sou_chain
                            PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/include" "${CMAKE_CURRENT_BINARY_DIR}/include"
                                   "${CMAKE_CURRENT_SOURCE_DIR}/../wasm-jit/Include"
                                   "${CMAKE_CURRENT_SOURCE_DIR}/libraries/sou-vm/include"
                                   "${CMAKE_SOURCE_DIR}/libraries/wabt"
                                   "${CMAKE_BINARY_DIR}/libraries/wabt"
                            )

if("sou-vm-oc" IN_LIST SOU_WASM_RUNTIMES)
   target_link_libraries(sou_chain "-Wl,-wrap=main")
endif()

foreach(RUNTIME ${SOU_WASM_RUNTIMES})
   string(TOUPPER "${RUNTIME}" RUNTIMEUC)
   string(REPLACE "-" "_" RUNTIMEUC ${RUNTIMEUC})
   target_compile_definitions(sou_chain PUBLIC "SOU_${RUNTIMEUC}_RUNTIME_ENABLED")
endforeach()

if(SOUVMOC_ENABLE_DEVELOPER_OPTIONS)
   message(WARNING "SOU VM OC Developer Options are enabled; these are NOT supported")
   target_compile_definitions(sou_chain PUBLIC SOU_VM_OC_DEVELOPER)
endif()

install( TARGETS sou_chain
   RUNTIME DESTINATION ${CMAKE_INSTALL_FULL_BINDIR}
   LIBRARY DESTINATION ${CMAKE_INSTALL_FULL_LIBDIR}
   ARCHIVE DESTINATION ${CMAKE_INSTALL_FULL_LIBDIR}
)
install( DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/include/sou/chain/
      DESTINATION ${CMAKE_INSTALL_FULL_INCLUDEDIR}/sou/chain
      FILES_MATCHING PATTERN "*.hpp" PATTERN "*.h" EXCLUDE
)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/include/sou/chain/core_symbol.hpp DESTINATION ${CMAKE_INSTALL_FULL_INCLUDEDIR}/sou/chain)
#if(MSVC)
#  set_source_files_properties( db_init.cpp db_block.cpp database.cpp block_log.cpp PROPERTIES COMPILE_FLAGS "/bigobj" )
#endif(MSVC)
