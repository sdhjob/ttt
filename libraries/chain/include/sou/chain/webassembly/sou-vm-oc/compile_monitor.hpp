#pragma once

#include <sou/chain/webassembly/sou-vm-oc/config.hpp>

#include <boost/asio/local/datagram_protocol.hpp>
#include <sou/chain/webassembly/sou-vm-oc/ipc_helpers.hpp>

namespace sou { namespace chain { namespace souvmoc {

wrapped_fd get_connection_to_compile_monitor(int cache_fd);

}}}