# ##################################################################################################
# Defines the sou-vm library and associated tooling. See docs/cmake.md for instructions on how to
# build sou-vm or integrate with another system with CMake.
# ##################################################################################################
cmake_minimum_required(VERSION 3.8)
set(VERSION_MAJOR 1)
set(VERSION_MINOR 0)
set(VERSION_PATCH 0)
set(VERSION_SUFFIX rc1)
project(sou-vm VERSION ${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH})

if (VERSION_SUFFIX)
   set(VERSION_FULL "${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}-${VERSION_SUFFIX}")
else()
   set(VERSION_FULL "${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}")
endif()

message(STATUS "Building sou-vm v${VERSION_FULL}...")

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_EXTENSIONS ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(CMAKE_THREAD_PREFER_PTHREAD TRUE)
find_package(Threads)
link_libraries(Threads::Threads)

# ##################################################################################################
# Gate against Windows builds. 
# ##################################################################################################
if (WIN32)
   message(FATAL_ERROR "SOU-VM currently only builds on Unix like OSes (Linux, Mac OSX)")
endif()

# ##################################################################################################
# Defined options for building or integrating sou-vm.
# ##################################################################################################
include(CMakeDependentOption)
option(ENABLE_SOFTFLOAT "enable the backend to use deterministic software floating point operations"
	ON)
option(FULL_DEBUG_BUILD "enables stack dumping and instruction tracing" OFF)
option(ENABLE_INSTALL "enable this library to be installed" ON)
option(ENABLE_MEMORY_OPS_ALIGNMENT "enable the backend to obey alignment hints" OFF)
option(ENABLE_TOOLS "enable building of tools" ON)
option(ENABLE_TESTS "enable building of unit tests, spec tests" OFF)
cmake_dependent_option(ENABLE_FUZZ_TESTS "enable fuzz testing" OFF "ENABLE_TESTS" ON)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/modules")
include(VMBuildUtils)

# ##################################################################################################
# Create the sou-vm library.
# ##################################################################################################
add_library(sou-vm INTERFACE)
target_include_directories(sou-vm
                           INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include
                                     ${CMAKE_CURRENT_SOURCE_DIR}/external/softfloat/source/include
                                     ${CMAKE_CURRENT_SOURCE_DIR}/external/outcome/single-header)

# ##################################################################################################
# Enable debugging stats for sou-vm.
# ##################################################################################################
if(FULL_DEBUG_BUILD)
   target_compile_definitions(sou-vm INTERFACE -DSOU_VM_FULL_DEBUG)
endif()

# ##################################################################################################
# Option specific build configurations.
# ##################################################################################################
if(ENABLE_SOFTFLOAT)
   if(NOT TARGET softfloat)
      add_subdirectory(external)
   endif()
   target_compile_definitions(sou-vm INTERFACE -DSOU_VM_SOFTFLOAT)
   target_link_libraries(sou-vm INTERFACE softfloat)
endif()

if(NOT USE_EXISTING_BOOST)
   target_compile_definitions(sou-vm INTERFACE -DSOU_VM_USE_EXTERNAL_OUTCOME)
   add_subdirectory(external/outcome)
endif()

if(ENABLE_MEMORY_OPS_ALIGNMENT)
   target_compile_definitions(sou-vm INTERFACE -DSOU_VM_ALIGN_MEMORY_OPS)
endif()

# ##################################################################################################
# Build sou-vm tools.
# ##################################################################################################
if(ENABLE_TOOLS)
add_subdirectory(tools)
endif()

# ##################################################################################################
# Installation.
# ##################################################################################################
if(ENABLE_INSTALL)
   include(GNUInstallDirs)
   message(STATUS "Installing...")
   install(TARGETS sou-vm
            LIBRARY
               DESTINATION ${CMAKE_INSTALL_LIBDIR}
               COMPONENT Libraries
            PUBLIC_HEADER
               DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
               COMPONENT Headers)

   install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/include/sou
      DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
endif()

