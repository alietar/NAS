import json

from utils import log
from utils.models import *
import router_connector

def read_intents(path: str) -> tuple[dict[str, typing.Any], dict[str, typing.Any], IPVersion, bool]:
    log.console.print(f"Intent file is [b]{path}[/b]")
    
    ### File reading
    try:
        log.info("Reading the intent file...")

        f = open(path, "r", encoding="utf-8")
        intents = json.load(f)
        f.close()
        
        log.success("Read the intents")
    except Exception as exp:
        log.fatal_error("Failed to read the intent file", exp)


    ### Check if we use gnsfy
    gns_config: dict[str, typing.Any] = intents.get("gns_auto_config", {})
    use_gnsfy = gns_config.get("enable", False)
    

    ### Register choosen IP version
    try:
        ip_version = IPVersion(intents.get("ip_version", "ipv4"))
    except:
        log.fatal_error(f"Invalid config for IP version", Exception(f"{intents.get("ip_version")} is not a valid ip version, use ipv4 or ipv6.")) 


    ## Check if there is enough addresses for the manual way to give addresses
    nb_links = len(intents.get("links", []))
    nb_routers = len(intents.get("routers", []))

    if not gns_config["auto_create_address"]["physical"]:
        if len(intents["address_pool"]["physical"]) < nb_links:
            log.fatal_error("Pas assez d'adresses physiques", Exception("address_pool.physical"))

    if not gns_config["auto_create_address"]["Loopback"]:
        if len(intents["address_pool"]["Loopback"]) < nb_routers:
            log.fatal_error("Pas assez d'adresses loopback", Exception("address_pool.Loopback"))
        

    return intents, gns_config, ip_version, use_gnsfy


def parse_routers_as(intents):
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

        write = router_data.get("write",False) or intents.get("write",False)

        port = router_data.get("port")
        host = router_data.get("host")

        routers[name] = Router(name, asn, as_list[asn], host, port, write=write)
        as_list[asn].routers[name] = routers[name]

    return as_list, routers