#pragma once

#include <sou/chain/types.hpp>
#include <sou/chain/contract_types.hpp>

namespace sou { namespace chain {

   class apply_context;

   /**
    * @defgroup native_action_handlers Native Action Handlers
    */
   ///@{
   void apply_sou_newaccount(apply_context&);
   void apply_sou_updateauth(apply_context&);
   void apply_sou_deleteauth(apply_context&);
   void apply_sou_linkauth(apply_context&);
   void apply_sou_unlinkauth(apply_context&);

   /*
   void apply_sou_postrecovery(apply_context&);
   void apply_sou_passrecovery(apply_context&);
   void apply_sou_vetorecovery(apply_context&);
   */

   void apply_sou_setcode(apply_context&);
   void apply_sou_setabi(apply_context&);

   void apply_sou_canceldelay(apply_context&);
   ///@}  end action handlers

} } /// namespace sou::chain
