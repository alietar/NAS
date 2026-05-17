import yaml
import os

from ..utils import log
from .models import *

from typing import Any

# Implementation of include in yaml
class YamlIncludeLoader(yaml.SafeLoader):
    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super(YamlIncludeLoader, self).__init__(stream)

def include_constructor(loader: YamlIncludeLoader, node: yaml.nodes.ScalarNode):
    filename = os.path.join(loader._root, loader.construct_scalar(node))
    with open(filename, 'r', encoding="utf-8") as f:
        return yaml.load(f, YamlIncludeLoader)

YamlIncludeLoader.add_constructor('!include', include_constructor)


def parse_intents(path: str) -> tuple[dict[str, typing.Any], dict[str, typing.Any], IPVersion, bool]:
    log.console.print(f"Intent file is [b]{path}[/b]")
    
    ### File reading
    try:
        log.info("Reading the intent file...")

        with open(path, "r", encoding="utf-8") as f:
            # On utilise safe_load pour éviter l'exécution de code arbitraire contenu dans le YAML
            intents = yaml.load(f, Loader=YamlIncludeLoader)
        
        log.success("Read the intents")
    except Exception as exp:
        log.fatal_error("Failed to read the intent file", exp)

    project_config: dict[str, Any] = intents.get("project", {})
    gns_config: dict[str, typing.Any] = intents.get("gns", {})

    # Check if we use gnsfy
    use_gnsfy = gns_config.get("enable", False)
    
    # Register choosen IP version
    try:
        ip_version = IPVersion(intents.get("ip_version", "ipv4"))
    except:
        log.fatal_error(f"Invalid config for IP version", Exception(f"{intents.get("ip_version")} is not a valid ip version, use ipv4 or ipv6.")) 


    # Check if there is enough addresses for the manual way to give addresses
    nb_links = len(intents.get("links", []))
    nb_routers = len(intents.get("routers", []))

    auto_create_address: dict[str, typing.Any] = project_config.get("auto_create_address", {})

    if not auto_create_address.get("physical"):
        if len(intents["address_pool"]["physical"]) < nb_links:
            log.fatal_error("Pas assez d'adresses physiques", Exception("address_pool.physical"))

    if not auto_create_address.get("Loopback"):
        if len(intents["address_pool"]["Loopback"]) < nb_routers:
            log.fatal_error("Pas assez d'adresses loopback", Exception("address_pool.Loopback"))
        

    return intents, gns_config, ip_version, use_gnsfy


def parse_routers_as(intents: dict[str, typing.Any]):
    """
    Creates the router and as objects from the intents dict
    
    :param intents: Intents
    :type intents: dict[str, typing.Any]
    """

    ### --- AS creation --- ###
    as_list: dict[int, AS] = {}
    for as_data in intents.get("as", []):
        asn = as_data["asn"]
        
        if as_list.get(asn) != None: # Verify ASN isn't already used
            log.fatal_error(f"Invalid config for AS n°{asn}", Exception(f"AS n°{asn} already exists")) 

        as_list[asn] = AS(
            asn,
            as_data["internal_protocol"].lower(),
            as_data["bgp_deployement"].lower(),
            as_data["redistribute_internal"]
        )
    
    # Relationships with other ASs
    for rel in intents.get("client_provider_relationships", []):
        as_list[rel["client"]].relationships.append(Relationship("client", as_list[rel["provider"]]))
        as_list[rel["provider"]].relationships.append(Relationship("provider", as_list[rel["client"]]))

    for rel in intents.get("peer_to_peer_relationships", []):
        as_list[rel["peer_1"]].relationships.append(Relationship("peer", as_list[rel["peer_2"]]))
        as_list[rel["peer_2"]].relationships.append(Relationship("peer", as_list[rel["peer_1"]]))


    ### --- Router creation --- ###
    routers: dict[int, Router] = {}

    for router_data in intents["routers"]:
        name: str = router_data["name"]
        asn: int = router_data["asn"]
        id: int = router_data.get("id")

        if id is not None and routers.get(id) is not None: # Verify id is free
            log.fatal_error(f"Invalid config for router {name}", Exception(f"ID {id} already used")) 

        if id is None: # Find the next id available
            id = 0
            while(routers.get(id) is not None):
                id += 1

        if as_list.get(asn) is None:
            log.fatal_error(f"Invalid config for router {name}", Exception(f"No AS n°{asn} found in intents")) 

        write = router_data.get("write", False) or intents.get("project", {}).get("write", False)

        port = router_data.get("port")
        host = router_data.get("host")

        routers[id] = Router(name, asn, as_list[asn], host, port, id, write=write)
        as_list[asn].routers[id] = routers[id]

    return as_list, routers