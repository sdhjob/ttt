#include <sou/chain/webassembly/sou-vm-oc.hpp>
#include <sou/chain/wasm_sou_constraints.hpp>
#include <sou/chain/wasm_sou_injection.hpp>
#include <sou/chain/apply_context.hpp>
#include <sou/chain/exceptions.hpp>

#include <vector>
#include <iterator>

namespace sou { namespace chain { namespace webassembly { namespace souvmoc {

class souvmoc_instantiated_module : public wasm_instantiated_module_interface {
   public:
      souvmoc_instantiated_module(const digest_type& code_hash, const uint8_t& vm_version, souvmoc_runtime& wr) :
         _code_hash(code_hash),
         _vm_version(vm_version),
         _souvmoc_runtime(wr)
      {

      }

      ~souvmoc_instantiated_module() {
         _souvmoc_runtime.cc.free_code(_code_hash, _vm_version);
      }

      void apply(apply_context& context) override {
         const code_descriptor* const cd = _souvmoc_runtime.cc.get_descriptor_for_code_sync(_code_hash, _vm_version);
         SOU_ASSERT(cd, wasm_execution_error, "SOU VM OC instantiation failed");

         _souvmoc_runtime.exec.execute(*cd, _souvmoc_runtime.mem, context);
      }

      const digest_type              _code_hash;
      const uint8_t                  _vm_version;
      souvmoc_runtime&               _souvmoc_runtime;
};

souvmoc_runtime::souvmoc_runtime(const boost::filesystem::path data_dir, const souvmoc::config& souvmoc_config, const chainbase::database& db)
   : cc(data_dir, souvmoc_config, db), exec(cc) {
}

souvmoc_runtime::~souvmoc_runtime() {
}

std::unique_ptr<wasm_instantiated_module_interface> souvmoc_runtime::instantiate_module(const char* code_bytes, size_t code_size, std::vector<uint8_t> initial_memory,
                                                                                     const digest_type& code_hash, const uint8_t& vm_type, const uint8_t& vm_version) {

   return std::make_unique<souvmoc_instantiated_module>(code_hash, vm_type, *this);
}

//never called. SOU VM OC overrides eosio_exit to its own implementation
void souvmoc_runtime::immediately_exit_currently_running_module() {}

}}}}
