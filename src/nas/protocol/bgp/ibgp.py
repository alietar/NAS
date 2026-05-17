from ... import commands 
from ...utils.ip_utils import *
    ##### iBGP config

def ibgp_config(routers: dict[int, Router], as_list: dict[int, AS], intents, gns_config, ip_version) -> None:
    for asn, a_s in as_list.items():
        ### Full mesh iBGP sessions
        for id, r in a_s.routers.items():
            no_bgp = a_s.bgp_deployement == "border" and not r.is_border

            if no_bgp:
                continue

            r.append_cmds(commands.enter_bgp_config(asn))

            for id_other, r_other in a_s.routers.items():
                if (a_s.bgp_deployement == "border" and not r_other.is_border) or id_other == id:
                    continue

                if ip_version == IPVersion.IPV4:
                    other_ip_without_mask = remove_ipv4_mask(r_other.interfaces["Loopback0"].addrs[0])
                else:
                    other_ip_without_mask = remove_ipv6_mask(r_other.interfaces["Loopback0"].addrs[0])

                address_family: str = ip_version.value
                address_family += " unicast"

                r.append_cmds(commands.i_bgp_neighbor(
                    other_ip_without_mask,
                    asn,
                    "Loopback0",
                    address_family,
                    # Next hop self is necessary for the internal routers to
                    # know where to route their packets going outside the AS
                    next_hope_self=r.is_border
                ))

                # Add the iBGP border router in the vref address family
                for interface in r.interfaces.values():
                    for other_interface in r_other.interfaces.values():
                        if interface.vrf and interface.vrf == other_interface.vrf:
                            address_family = f"vpnv4"

                            r.append_cmds(commands.bgp_address_family(
                                other_ip_without_mask,
                                address_family,
                                # Next hop self is necessary for the internal routers to
                                # know where to route their packets going outside the AS
                                next_hope_self=False
                                # next_hope_self=r.is_border
                            ))

            r.append_cmd("exit")

            ### Targetting only border router for community tagging
            if not r.is_border:
                continue

            if a_s.redistribute_internal:
                if a_s.internal_protocol == "ospf":
                    process_id = r.id
                else:
                    process_id = "RIP_AS"
                
                address_family = ip_version.value + " unicast"

                r.append_cmds(commands.redistribute_iBGP(asn, a_s.internal_protocol, process_id, address_family))

        ### Route tagging
        # rel means a relationship
        for rel in a_s.relationships:
            for link in rel.links:
                tag_community(intents, asn, link, rel.type, ip_version)
            
        ### appliquer les conditions en fonction de la relation entre les AS
        apply_community_conditions(a_s, ip_version)

def tag_community(intents, asn: int, link: RelationshipLink, type: str, ip_version: IPVersion):
    r = link.from_r
    constants = intents["community_constants"][type]

    # Value community is constructed with {asn}:{key}, the key depends on the type of relationship with the other AS
    value_community = f"{asn}:{constants["value_suffix"]}"

    r.append_cmds(commands.create_route_map(
        constants["route_map_tag"],
        ip_version,
        community=value_community,
        local_pref=constants["local_pref"],
    ))

    ### Aplying the route map for the routes incoming
    neighbor_ip_without_mask = remove_ipv6_mask(link.to_ip)

    r.append_cmds(commands.apply_route_map(
        neighbor_ip_without_mask,
        constants["route_map_tag"],
        asn,
        ip_version,
        True ### Need to verify
    ))

    r.append_cmds(commands.create_community_list(constants["community_list_name"], value_community))


def apply_community_conditions(a_s: AS, ip_version: IPVersion):
    block_list = []

    # If AS is client add PROVIDER to block list
    # If AS is peer to peer add PEER to block list
    for rel in a_s.relationships:
        if rel.type == "client" and "PROVIDER" not in block_list:
            block_list.append("PROVIDER")
        elif rel.type == "peer" and "PEER" not in block_list:
            block_list.append("PEER")

    for r in a_s.routers.values():
        if not r.is_border:
            continue

        if block_list:
            r.append_cmds(commands.create_route_map(
                "BLOCK_UPSTREAM",
                ip_version,
                deny=True,
                community_list=" ".join(block_list),
            ))

        ### Find other AS router ip

        for rel, link in a_s.get_relationships_from(r):
            if rel.type in ("client", "peer") and block_list:
                r.append_cmds(commands.apply_route_map(remove_ipv6_mask(link.to_ip), "BLOCK_UPSTREAM", a_s.asn, ip_version, entry=False))