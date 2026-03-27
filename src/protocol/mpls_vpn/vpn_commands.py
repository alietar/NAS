def mpls_config(interface_name: str) -> list[str]:
    cmds = [
        f"interface {interface_name}",
        "mpls ip",
        "exit",
    ]

    return cmds

def ldp_base_config() -> list[str]:
    cmds = [
        "mpls label protocol ldp",
        "mpls ldp router-id Loopback0 force"
    ]

    return cmds

def vrf_config(client_name: str, route_distinguisher: str, route_target: str) -> list[str]:
    cmds = [
        f"ip vrf {client_name}",
        f"rd {route_distinguisher}",
        f"route-target export {route_target}",
        f"route-target import {route_target}",
        "exit",
    ]

    return cmds

def vrf_interface_forwarding_config(interface_name:str, client_name: str) -> list[str]:
    cmds = [
        f"interface {interface_name}",
        f"ip vrf forwarding {client_name}",
        "exit",
    ]

    return cmds