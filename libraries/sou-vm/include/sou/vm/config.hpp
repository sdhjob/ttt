#pragma once

namespace sou { namespace vm {

// create constexpr flags for whether the backend should obey alignment hints
#ifdef SOU_VM_ALIGN_MEMORY_OPS
   inline constexpr bool should_align_memory_ops = true;
#else
   inline constexpr bool should_align_memory_ops = false;
#endif


#ifdef SOU_VM_SOFTFLOAT
   inline constexpr bool use_softfloat = true;
#else
   inline constexpr bool use_softfloat = false;
#endif

#ifdef SOU_VM_FULL_DEBUG
   inline constexpr bool sou_vm_debug = true;
#else
   inline constexpr bool sou_vm_debug = false;
#endif

}} // namespace sou::vm
