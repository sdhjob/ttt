#pragma once

#include <sou/chain/webassembly/sou-vm-oc/config.hpp>
#include <sou/chain/webassembly/sou-vm-oc/sou-vm-oc.hpp>
#include <sou/chain/types.hpp>

namespace sou { namespace chain { namespace souvmoc {

struct initialize_message {
   //Two sent fds: 1) communication socket for this instance  2) the cache file 
};

struct initalize_response_message {
   fc::optional<std::string> error_message; //no error message? everything groovy
};

struct code_tuple {
   sou::chain::digest_type code_id;
   uint8_t vm_version;
   bool operator==(const code_tuple& o) const {return o.code_id == code_id && o.vm_version == vm_version;}
};

struct compile_wasm_message {
   code_tuple code;
   //Two sent fd: 1) communication socket for result, 2) the wasm to compile
};

struct evict_wasms_message {
   std::vector<code_descriptor> codes;
};

struct code_compilation_result_message {
   souvmoc_optional_offset_or_import_t start;
   unsigned apply_offset;
   int starting_memory_pages;
   unsigned initdata_prologue_size;
   //Two sent fds: 1) wasm code, 2) initial memory snapshot
};


struct compilation_result_unknownfailure {};
struct compilation_result_toofull {};

using wasm_compilation_result = fc::static_variant<code_descriptor,  //a successful compile
                                                  compilation_result_unknownfailure,
                                                  compilation_result_toofull>;

struct wasm_compilation_result_message {
   code_tuple code;
   wasm_compilation_result result;
   size_t cache_free_bytes;
};

using souvmoc_message = fc::static_variant<initialize_message,
                                           initalize_response_message,
                                           compile_wasm_message,
                                           evict_wasms_message,
                                           code_compilation_result_message,
                                           wasm_compilation_result_message
                                          >;
}}}

FC_REFLECT(sou::chain::souvmoc::initialize_message, )
FC_REFLECT(sou::chain::souvmoc::initalize_response_message, (error_message))
FC_REFLECT(sou::chain::souvmoc::code_tuple, (code_id)(vm_version))
FC_REFLECT(sou::chain::souvmoc::compile_wasm_message, (code))
FC_REFLECT(sou::chain::souvmoc::evict_wasms_message, (codes))
FC_REFLECT(sou::chain::souvmoc::code_compilation_result_message, (start)(apply_offset)(starting_memory_pages)(initdata_prologue_size))
FC_REFLECT(sou::chain::souvmoc::compilation_result_unknownfailure, )
FC_REFLECT(sou::chain::souvmoc::compilation_result_toofull, )
FC_REFLECT(sou::chain::souvmoc::wasm_compilation_result_message, (code)(result)(cache_free_bytes))