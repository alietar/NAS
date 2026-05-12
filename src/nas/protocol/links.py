import ipaddress

from ..utils.models import *
from .. import commands
from ..utils import log
from ..utils import ip_utils

def link_config(routers: dict[str, Router], as_list: dict[int, AS], intents, gns_config, ip_version) -> None:
    ### Link and protocol setup
    cpt_link = 0
    cond_creation_address = intents["gns_auto_config"]["auto_create_address"]["physical"]
    for link in intents["links"]:
        router_a: Router = routers[link["from"]]
        router_b: Router = routers[link["to"]]
        interface_a: str = link["interface_from"]
        interface_b: str = link["interface_to"]
        
        cost_from, cost_to = read_ospf_cost(link)

        # Configure the interface for both routers of the link
        if cond_creation_address:
            addr_a, addr_b = ip_utils.compute_ip_address(router_a, router_b, ip_version)
        else:
            addr_a, addr_b = intents["address_pool"]["physical"][cpt_link][0], intents["address_pool"]["physical"][cpt_link][1]

        configure_one_interface(router_a, router_b, interface_a, addr_a, addr_b, ip_version, cost_from)
        configure_one_interface(router_b, router_a, interface_b, addr_b, addr_a, ip_version, cost_to)
        
        cpt_link +=1


def read_ospf_cost(link):
    if "ospf_cost" not in link:
        return None, None
    cost = link["ospf_cost"]
    if isinstance(cost, dict):
        return cost.get("from"), cost.get("to")
    return cost, cost


def configure_one_interface(r_a: Router, r_b: Router, interface_a: str, addr_a:str, addr_b:str, ip_version: IPVersion, opsf_cost=None):
    log.info(f"Configuring {interface_a} on {r_a.name}")
    
    r_a.append_cmds(commands.address_config(interface_a, addr_a, ip_version))

    r_a.interfaces[interface_a].add_addr(addr_a)
    r_a.interfaces[interface_a].neighbor_router = r_b
    
    # Internal protocol setup
    if r_a.asn == r_b.asn: # Same as
        r_a.interfaces[interface_a].is_internal = True
        protocol = r_a.a_s.internal_protocol

        if protocol == "rip":
            log.info(f"Enabling RIP")
            r_a.append_cmds(commands.rip_config(addr_a, interface_a, r_a.name, ip_version))

        elif protocol == "ospf":
            log.info(f"Enabling OSPF")
            r_a.append_cmds(commands.ospf_config(addr_a, interface_a, r_a.name, 0, ip_version, opsf_cost))

    # Inter as protocol AKA eBGP
    else: # Different as
        log.info(f"Enabling eBGP")

        r_a.is_border = True
        
        if ip_version == IPVersion.IPV4:
            addr_a_without_mask = ip_utils.remove_ipv4_mask(addr_a)
            addr_b_without_mask = ip_utils.remove_ipv4_mask(addr_b)

            prefix_a = ".".join(addr_a_without_mask.split(".")[:-1]) + ".0" + " mask 255.255.255.0"
        else:
            addr_a_without_mask = ip_utils.remove_ipv6_mask(addr_a)
            addr_b_without_mask = ip_utils.remove_ipv6_mask(addr_b)
            
            prefix_a = str(ipaddress.IPv6Interface(addr_a).network)

        r_a.append_cmds(commands.bgp_advertise_network(r_a.asn, prefix_a, ip_version))

        r_a.append_cmds(commands.e_bgp_neighbor_config(r_a.asn, addr_b_without_mask, r_b.asn, ip_version))

        r_a.append_cmds(commands.send_community(r_a.asn, addr_b_without_mask, ip_version))

        ### Find the corresponding relationship for this inter-as link
        # Loops through the relationship to see which one has the router
        # And then add the router to the relationship class to find it more easily after
        for rel in r_a.a_s.relationships:
            if rel.other.routers.get(r_b.name) is not None: # The other AS has the other router so it is the AS correponsing with the relationship
                rel.links.append(RelationshipLink(
                    r_a,
                    addr_a,
                    r_b,
                    addr_b
                ))