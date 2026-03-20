def base_router_config(name):
    return [
        "enable",
        "configure terminal",
        f"hostname {name}",
        "ipv6 unicast-routing"
    ]


def address_config(interface, address):
    return [
        f"interface {interface}",
        "ipv6 enable",
        f"ipv6 address {address}",
        "no shutdown",
        "exit"
    ]

def loopback_config(address, protocol, process):
    cmds = address_config("Loopback0", address)[:-2]

    if protocol == "ospf":
        cmds += [
            f"ipv6 ospf {process} area 0",
            "exit"
        ]

    elif protocol == "rip":
        process = "RIP_AS"
        cmds += [
            f"ipv6 RIP {process} enable",
            "exit"
        ]

    return cmds

def rip_config(address, interface, name):
    process_name = "RIP_AS"
    conf = []
    # conf += baseRouterConfig(name)
    # conf += addressConfig(interface,address)
    conf += [
        # f"ipv6 router rip {process_name}",
        # f"interface {interface}",
        # "exit",
        f"interface {interface}",
        f"ipv6 rip {process_name} enable",
        "exit"
    ]

    return conf


def ospf_config(address, interface, name, area_nb, cost=None):
    conf = []
    process_id = int(name[1:])
    # conf += baseRouterConfig(name)
    # conf += addressConfig(interface,address)

    conf += [
        f"ipv6 router ospf {process_id}",
        f"router-id {process_id}.{process_id}.{process_id}.{process_id}",
        "exit",
        f"interface {interface}",
        f"ipv6 ospf {process_id} area {area_nb}",
        ]

    if cost is not None:
        conf.append(f"ipv6 ospf cost {int(cost)}")
    
    conf.append("exit")
    

    return conf


   #"redistribute connected" à activer si on veut partager tous les sous reseaux auxquels on appartient, ce qui n'est pas le cas tout le temps :)


def enter_bgp_config(asn):
    return [ f"router bgp {asn}" ]


def i_bgp_neighbor(other_ip, asn, loopback_interface_name, next_hope_self=False):
    cmds = [
        f"neighbor {other_ip} remote-as {asn}",
        f"neighbor {other_ip} update-source {loopback_interface_name}",
        f"address-family ipv6 unicast",
        f"neighbor {other_ip} activate",
        f"neighbor {other_ip} send-community both"]
    
    if next_hop_self:
        cmds.append(f"neighbor {other_ip} next-hop-self")

    cmds += ["exit-address-family"]

    return cmds


def bgp_config(router_id, as_nb):
    return [
        f"router bgp {as_nb}", # Enters BGP configuration
        f"bgp router-id {router_id}.{router_id}.{router_id}.{router_id}",
        f"no bgp default ipv4-unicast",
        f"exit"
    ]

def bgp_advertise_network(as_nb, prefix):
    return [
        f"router bgp {as_nb}",
        "address-family ipv6 unicast",
        f"network {prefix}",
        "exit-address-family",
        "exit",
    ]



def e_bgp_neighbor_config(as_nb, neighbor_ip, neighbor_as_nb):
    return [
        f"router bgp {as_nb}", # Enters BGP configuration
        f"neighbor {neighbor_ip} remote-as {neighbor_as_nb}", # Enters neighbor config
        f"address-family ipv6 unicast",
        f"neighbor {neighbor_ip} activate",
        f"exit-address-family", ### !!! Maybe is useless because of the end command
        f"exit"]



def redistribute_iBGP(as_number, protocol, process_id): ## à faire que sur les routeurs de bordure pour annoncer les routes à BGP
    """
    Redistribue un IGP (OSPF ou RIP) dans BGP 
    """
    protocol = protocol.lower()

    return [
        f"router bgp {as_number}",
        "address-family ipv6 unicast",
        f"redistribute {protocol} {process_id}",
        "exit-address-family",
        "exit"
    ]


def next_hop_self(as_number, neighbors):
    if isinstance(neighbors, str):
        neighbors = [neighbors]

    cmds = [
        f"router bgp {as_number}",
        "address-family ipv6 unicast",
    ]
    for ip in neighbors:
        cmds.append(f"neighbor {ip} next-hop-self")

    cmds += [
        "exit-address-family",
        "exit",
    ]
    return cmds



# address_blocked_list = 
# [
#     {"adress_blocked" : value , "for_who" : [addresses] }        addreses peut valoir "any"
#     {"adress_blocked" : value , "for_who" : [addresses] }
# ]



def create_access_list(address_blocked_list, name_acl, deny):     #deny = true => blocked address  deny = false => route autorisee
    conf = [
        "enable",
        "configure terminal",
        f"ipv6 access-list {name_acl} "
           ]
    for dico in address_blocked_list:
        for address in dico["for_who"]:
            if deny:
                conf.append(f"deny {dico["address_blocked"]} {address}")
            else:
                conf.append(f"permit {dico["address_blocked"]} {address}")
    #bonne pratique : conf.append("permit ipv6 any any")
    conf.append("end")
    conf.append(" ")
    return conf



# def create_route_map(map_tag, name_acl, sequence_number, deny=True):
#     conf = [
#         "enable",
#         "configure terminal"
#     ]

#     action = "deny" if deny else "permit"
#     conf.append(f"route-map {map_tag} {action} {sequence_number}")
#     conf.append(f" match ipv6 address {name_acl}")

#     # obligatoire sinon ils les deny all
#     conf.append(f"route-map {map_tag} permit {sequence_number + 10}")

#     conf += [
#         "end",
#         " "
#     ]

#     return conf

def create_route_map(map_tag, sequence_number=10, name_acl=None, deny=False, community=None, community_list=None, local_pref=None):
    conf = []

    action = "deny" if deny else "permit"

    conf.append(f"route-map {map_tag} {action} {sequence_number}")

    if name_acl:
        conf.append(f"match ipv6 address {name_acl}")

    if community:
        if deny:
            raise ValueError(
                "Impossible de définir une community dans une route-map deny")
        conf.append(f"set community {community}")

    if community_list:
        conf.append(f"match community {community_list}")
    
    if local_pref:
        conf.append(f"set local-preference {local_pref}")

    conf.append(f"route-map {map_tag} permit {sequence_number + 10}")

    conf += [
        "exit"
    ]

    return conf


def apply_route_map(address, map_tag, as_number, entry=True):
    conf = []
    conf += [
        f"router bgp {as_number}",
        "address-family ipv6 unicast"
             ]
    if entry:
        conf.append(f"neighbor {address} route-map {map_tag} in")
    else:
        conf.append(f"neighbor {address} route-map {map_tag} out")

    conf.append("exit")
    conf.append("exit")
    return conf


def enable_community(): # à faire sur tous les routeurs pour qu'ils comprennent quand on fait  f" set community {community}"
    return [ "ip bgp-community new-format" ]

def create_community_list(name, community, permit=True):
    action = "permit" if permit else "deny"

    return [
        f"ip community-list standard {name} {action} {community}"
    ]


def send_community(as_nb, neighbor_addr):
    return [
        f"router bgp {as_nb}",
        "address-family ipv6 unicast",
        f"neighbor {neighbor_addr} send-community both",
        "exit-address-family",
        "exit",
    ]

       

#################################################################
#Comment initialiser une community et appliquer une règle dessus#
#################################################################

## Je fais un premier create_route_map puis apply_route_map 
# qui tag toutes les routes. Après je créé la community-list lié 
# avec le numéro de community puis j'applique la règle que je veux



    





