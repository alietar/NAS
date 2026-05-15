from ...utils.models import *
from .vpn_commands import *

def apply_vpn(routers: dict[int, Router], as_list: dict[int, AS], intents) -> None:
    vpn_config = intents.get("vpn")

    if vpn_config is None:
        return

    client_id_name_pair: dict[str, int] = {}
    
    for vpn in vpn_config:
        provider_as = as_list[vpn["provider_asn"]]
        client_asn_list = vpn["client_asn_list"]
        client_name = vpn["client_name"]

        for router in provider_as.routers.values():
            for interface in router.interfaces.values():
                if len(interface.addrs) == 0 or interface.is_loopback:
                    continue

                # Activate mpls on every Loopback interface of the AS
                if interface.is_internal:
                    router.append_cmds(mpls_config(interface.name))

                # Enable vrf on external interface on PE router
                else:
                    if router.is_border and interface.neighbor_router.asn in client_asn_list:
                        if not client_id_name_pair.get(client_name):
                            client_id_name_pair[client_name] = len(client_id_name_pair) + 1
                        
                        client_id = client_id_name_pair[client_name]

                        route_distinguisher = f"{provider_as.asn}:{client_id}"
                        route_target = f"{provider_as.asn}:{client_id*100}"

                        router.append_cmds(vrf_interface_forwarding_config(interface.name, client_name))
                        router.append_cmds(vrf_config(client_name, route_distinguisher, route_target))


            # Enable ldp
            router.append_cmds(ldp_base_config())