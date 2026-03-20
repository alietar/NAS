### Native libraries
import json
import multiprocessing
import typing
import ipaddress
import time

### Added libraries
import click
from rich.pretty import pprint

### Own libraries
import gns
import commands
from ip_utils import *
import log
from log import console
from utils import *
from display import router_coords_from_intent



### CLI Arguments
@click.command()
@click.argument('intentfile', type=click.Path(exists=True, readable=True), default="./intents/intent_2_AS_OSPF_RIP.json")
def main(intentfile):
    console.print("[b][blue]Cisco routers configuration tool[/b][/blue]")
    console.print(f"Intent file is [b]{intentfile}[/b]")

    cmds = {}
    adress = {}

    ### Reading the intent file
    intents = read_intents(intentfile)


    ### Check if we use gnsfy
    use_gnsfy = False    
    gns_config: dict[str, typing.Any] = intents.get("gns_auto_config")


    ## check if there is enough addresses for the manual way to give addresses
    nb_links = len(intents.get("links", []))
    nb_routers = len(intents.get("routers", []))

    if not gns_config["auto_create_address"]["physical"]:
        if len(intents["address_pool"]["physical"]) < nb_links:
            log.fatal_error("Pas assez d'adresses physiques", Exception("address_pool.physical"))

    if not gns_config["auto_create_address"]["Loopback"]:
        if len(intents["address_pool"]["Loopback"]) < nb_routers:
            log.fatal_error("Pas assez d'adresses loopback", Exception("address_pool.Loopback"))


    if gns_config and gns_config.get("enable"):
        use_gnsfy = True

    ### Project opening
    if use_gnsfy:
        g = open_gns(gns_config)


    ##### Creating data structures
    ### ASs
    as_list: dict[int, AS] = {}
    for as_data in intents["as"]:
        asn = as_data["asn"]
        
        if as_list.get(asn) != None:
            log.fatal_error(f"Invalid config for AS n°{asn}", Exception(f"AS n°{asn} already exists")) 
        
        internal_protocol = as_data["internal_protocol"].lower()

        as_list[asn] = AS(asn, internal_protocol)
    
    # Relationships with other ASs
    for rel in intents.get("client_provider_relationships", []):
        as_list[rel["client"]].relationships.append(Relationship("client", as_list[rel["provider"]]))
        as_list[rel["provider"]].relationships.append(Relationship("provider", as_list[rel["client"]]))

    for rel in intents.get("peer_to_peer_relationships", []):
        as_list[rel["peer_1"]].relationships.append(Relationship("peer", as_list[rel["peer_2"]]))
        as_list[rel["peer_2"]].relationships.append(Relationship("peer", as_list[rel["peer_1"]]))


    ### Routers
    routers: dict[str, Router] = {}

    for router_data in intents["routers"]:
        name: str = router_data["name"]
        asn: int = router_data["asn"]

        if as_list.get(asn) == None:
            log.fatal_error(f"Invalid config for router {name}", Exception(f"No AS n°{asn} found in intents")) 
        
        if routers.get(name) != None:
            log.fatal_error(f"Invalid config for router {name}", Exception(f"Router {name} already exists")) 
        
        # Getting host and port depending on choosed method,
        # either automaticaly from GNS or with the user's intents
        port = router_data.get("port")
        host = router_data.get("host")
        write = router_data.get("write",False) or intents.get("write",False)

        if use_gnsfy and gns_config.get("create_routers", False):
            try:
                log.info(f"Creating/recovering router {name} (GNS)")
                
                router_positions = router_coords_from_intent(
                    intents,
                    as_radius=400,
                    router_radius=80,
                    center=(0, 0),
                )


                # Creating/recovering router in GNS
                if gns_config.get("arrange_automagically", False):
                    pos = router_positions.get(name, {"x": 0, "y": 0})
                    g.create_router(name=name, auto_recover=True, x=pos["x"], y=pos["y"]) # Creating/recovering router in GNS
                else:
                    g.create_router(name=name, auto_recover=True)

            except Exception as exp:
                console.print_exception()
                log.fatal_error("Failed to create/recover the router {name} (GNS)", exp)

            if gns_config.get("auto_fetch_router_infos", False):
                port = g.get_router_port(name)
                host = gns_config.get("ip", "127.0.0.1")

        if host is None or port is None:
            if gns_config.get("auto_fetch_router_infos", False):
                log.fatal_error(f"Failed to fetch the host or port for {name}", Exception("Can't fetch host/port on GNS"))
            else:
                log.fatal_error(f"Failed to fetch the host or port for {name}", Exception("Can't get host/port in intent"))

        routers[name] = Router(name, asn, as_list[asn], host, port, write=write)
        as_list[asn].routers[name] = routers[name]

        # Basic router config
        routers[name].append_cmds(commands.base_router_config(name))
        routers[name].append_cmds(commands.enable_community()) # Mandatory for communities
    

    ### Link and protocol setup
    cpt_link = 0
    cond_creation_address = intents["gns_auto_config"]["auto_create_address"]["physical"]
    for link in intents["links"]:
        router_a: Router = routers[link["from"]]
        router_b: Router = routers[link["to"]]
        interface_a: str = link["interface_from"]
        interface_b: str = link["interface_to"]


        if gns_config.get("create_links", False):
            log.info(f"Adding link from {link["interface_from"]} on {link["from"]} to {link["interface_to"]} on {link["to"]} (GNS)")
            try:
                g.create_link(link["from"], # Adding link inside GNS
                            link["interface_from"],
                            link["to"],
                            link["interface_to"])
            except Exception as exp:
                log.fatal_error(f"Cannot create link from {link["interface_from"]} on {link["from"]} to {link["interface_to"]} on {link["to"]}, check if the interfaces are not used twice !!", exp)
            
        
        cost_from, cost_to = read_ospf_cost(link)

        # Configure the interface for both routers of the link
        if cond_creation_address:
            addr_a, addr_b = compute_ip_address(router_a, router_b)
        else:
            addr_a, addr_b = intents["address_pool"]["physical"][cpt_link][0], intents["address_pool"]["physical"][cpt_link][1]

        configure_one_interface(router_a, router_b, interface_a, addr_a, addr_b, cost_from)
        configure_one_interface(router_b, router_a, interface_b, addr_b, addr_a, cost_to)
        
        cpt_link +=1


    ### Enable BGP on every router
    for name, r in routers.items():
        r.append_cmds(commands.bgp_config(r.id, r.asn))


    ##### iBGP config
    cpt = 0
    for asn, a_s in as_list.items():
        ### Adding loopback address
        # We first need to enable the loopback interface on all the routers before configuring iBGP
        
        for name, r in a_s.routers.items():
            if gns_config.get("auto_create_address", False) and gns_config["auto_create_address"].get("Loopback", False):
                loopback_addr = compute_loopback_address(name, asn)

            else:
                loopback_addr = intents["address_pool"]["Loopback"][cpt]

            r.interfaces["Loopback0"].append(loopback_addr)
            r.append_cmds(commands.loopback_config(
                loopback_addr,
                a_s.internal_protocol,
                r.id))
            
            cpt += 1


        ### Full mesh iBGP sessions
        for name, r in a_s.routers.items():
            r.append_cmds(commands.enter_bgp_config(asn))

            for name_other, r_other in a_s.routers.items():
                if name_other == name:
                    continue

                other_ip_without_mask = remove_ipv6_mask(r_other.interfaces["Loopback0"][0])

                r.append_cmds(commands.i_bgp_neighbor(
                    other_ip_without_mask,
                    asn,
                    "Loopback0",
                    # Next hop self is necessary for the internal routers to
                    # know where to route their packets going outside the AS
                    next_hope_self=r.is_border
                ))

            r.append_cmd("exit")

            ### Targetting only border router for community tagging
            if not r.is_border:
                continue

            if a_s.internal_protocol == "ospf":
                process_id = r.id
            else:
                process_id = "RIP_AS"

            r.append_cmds(commands.redistribute_iBGP(asn, a_s.internal_protocol, process_id))

        ### Route tagging
        # rel means a relationship
        for rel in a_s.relationships:
            for link in rel.links:
                tag_community(intents, asn, link, rel.type)
            
        ### appliquer les conditions en fonction de la relation entre les AS
        apply_community_conditions(a_s)


    ### Start all router on GNS
    if use_gnsfy:
        with console.status("[blue] Starting routers (GNS)...") as status:
            for name in routers.keys():
                g.routers[name].start()

        log.success("Started routers (GNS)")

    with console.status("[blue] Waiting 10s for routers to start") as status:
        time.sleep(10)


    ### Telnet sending
    write_configs(routers)

    if use_gnsfy and gns_config.get("arrange_in_circle", False):
        g.lab.arrange_nodes_circular()
    
    console.print("\n[b][green]Finished![/b][/green]")



def tag_community(intents, asn: int, link: RelationshipLink, type: str):
    r = link.from_r
    constants = intents["community_constants"][type]

    # Value community is constructed with {asn}:{key}, the key depends on the type of relationship with the other AS
    value_community = f"{asn}:{constants["value_suffix"]}"

    r.append_cmds(commands.create_route_map(
        constants["route_map_tag"],
        community=value_community,
        local_pref=constants["local_pref"]
    ))

    ### Aplying the route map for the routes incoming
    neighbor_ip_without_mask = remove_ipv6_mask(link.to_ip)

    r.append_cmds(commands.apply_route_map(
        neighbor_ip_without_mask,
        constants["route_map_tag"],
        asn,
        True ### Need to verify
    ))

    r.append_cmds(commands.create_community_list(constants["community_list_name"], value_community))


def read_ospf_cost(link):
    if "ospf_cost" not in link:
        return None, None
    cost = link["ospf_cost"]
    if isinstance(cost, dict):
        return cost.get("from"), cost.get("to")
    return cost, cost



def apply_community_conditions(a_s: AS):
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
                deny=True,
                community_list=" ".join(block_list),
            ))

        ### Find other AS router ip

        for rel, link in a_s.get_relationships_from(r):
            if rel.type in ("client", "peer") and block_list:
                r.append_cmds(commands.apply_route_map(remove_ipv6_mask(link.to_ip), "BLOCK_UPSTREAM", a_s.asn, entry=False))



def write_configs(routers):
    processes = []

    with console.status("[blue] Sending commands to routers") as status:
        for r in routers.values():
            log.info(f"Starting Telnet to [b]{r.name}[/] on {r.host}://{r.port}")
        
            processes.append(multiprocessing.Process(target=r.send_cmds))
            processes[-1].start()

        for i in range(len(processes)):
            processes[i].join()



def configure_one_interface(r_a: Router, r_b: Router, interface_a: str, addr_a:str, addr_b:str, opsf_cost=None):
    log.info(f"Configuring {interface_a} on {r_a.name}")
    
    r_a.append_cmds(commands.address_config(interface_a, addr_a))

    r_a.interfaces[interface_a].append(addr_a)
    
    # Internal protocol setup
    if r_a.asn == r_b.asn: # Same as
        protocol = r_a.a_s.internal_protocol

        if protocol == "rip":
            log.info(f"Enabling RIP")
            r_a.append_cmds(commands.rip_config(addr_a, interface_a, r_a.name))

        elif protocol == "ospf":
            log.info(f"Enabling OSPF")
            r_a.append_cmds(commands.ospf_config(addr_a, interface_a, r_a.name, 0, opsf_cost))

    # Inter as protocol AKA eBGP
    else: # Different as
        log.info(f"Enabling eBGP")

        r_a.is_border = True

        addr_a_without_mask = remove_ipv6_mask(addr_a)
        addr_b_without_mask = remove_ipv6_mask(addr_b)
        
        prefix_a = str(ipaddress.IPv6Interface(addr_a).network)

        r_a.append_cmds(commands.bgp_advertise_network(r_a.asn, prefix_a))

        r_a.append_cmds(commands.e_bgp_neighbor_config(r_a.asn, addr_b_without_mask, r_b.asn))

        r_a.append_cmds(commands.send_community(r_a.asn, addr_b_without_mask))

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




def read_intents(path) -> dict[str, typing.Any] :
    try:
        log.info("Reading the intent file...")

        f = open(path, "r", encoding="utf-8")
        intents = json.load(f)
        f.close()
        
        log.success("Read the intents")
    except Exception as exp:
        log.fatal_error("Failed to read the intent file", exp)
        
    return intents



def open_gns(gns_config):
    log.info("Auto config is enabled, connecting to the server... (GNS)")

    try:
        g = gns.GnsProject(name=gns_config["project_name"], ip=gns_config.get("ip", "http://localhost"), port=gns_config.get("port", 3080))
        g.create_new(auto_recover=True)
        g.open()
    
        log.success("Opened/created the project (GNS)")

    except Exception as exp:
        log.fatal_error("Failed to connect to the GNS server", exp)

    return g



if __name__ == "__main__":
    main()