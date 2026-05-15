from __future__ import annotations
from enum import Enum
import typing

from . import log
from ..router_connector import telnet

class IPVersion(Enum):
    IPV4 = "ipv4"
    IPV6 = "ipv6"

class Router:
    def __init__(self, name: str, asn: int, a_s: AS, host: str, port: int, id: int, write:bool = False):
        self.name: str = name
        self.asn: int = asn
        self.a_s: AS = a_s
        self.host: str = host
        self.port: int = port
        self.write: bool = write
        self.id: int = id

        self.is_border: bool = False

        self.interfaces: dict[str, Interface] = {
            "Loopback0": Interface("Loopback0"),
            "g1/0": Interface("g1/0"),
            "g2/0": Interface("g2/0"),
            "g3/0": Interface("g3/0"),
            "g4/0": Interface("g4/0"),
        }

        self.cmds: list[str] = []
        self.a_s: AS 

    def append_cmd(self, cmd: str): # Single command
        self.cmds.append(cmd)
    
    def append_cmds(self, cmds: list[str]): # List of commands
        self.cmds += cmds

    def send_cmds(self):
        self.append_cmd("end")
        if self.write:
            self.append_cmd("write")
            self.append_cmd("")

        telnet.run_on_router(self.cmds, self.host, self.port)

        log.success(f"Finished config of [b]{self.name}[/]")


class Interface:
    def __init__(self, name:str, is_loopback:bool = False) -> None:
        self.name = name
        self.is_loopback = is_loopback
        self.is_internal = False 
        self.addrs: list[str] = []
        self.neighbor_router: Router 

    def add_addr(self, address: str):
        self.addrs.append(address)


class AS:
    def __init__(self, asn: int, internal_protocol: str, bgp_deployement: str):
        self.asn: int = asn
        self.internal_protocol: str = internal_protocol
        self.bgp_deployement: str = bgp_deployement

        if bgp_deployement != "every" and bgp_deployement != "border":
            log.fatal_error(f"Invalid config for AS n°{asn}", Exception("bgp deployement is not 'every' or 'border'")) 
        
        self.routers: dict[int, Router] = {}

        self.relationships: list[Relationship] = []

    def get_relationships_from(self, r: Router) -> list[tuple[Relationship, RelationshipLink]]:
        l: list[tuple[Relationship, RelationshipLink]] =[]

        for rel in self.relationships:
            for link in rel.links:
                if link.from_r == r:
                    l.append((rel, link))

        return l

class Relationship:
    def __init__(self, type: str, other: AS) -> None:
        self.type: str = type # If provider it means that self is a provider of the client other
        self.other: AS = other
        self.links: list[RelationshipLink] = []

class RelationshipLink:
    def __init__(self, from_r: Router, from_ip: str, to_r: Router, to_ip: str) -> None:
        self.from_r: Router = from_r
        self.from_ip: str = from_ip
        self.to_r: Router = to_r
        self.to_ip: str = to_ip