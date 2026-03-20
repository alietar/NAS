from __future__ import annotations
from enum import Enum
import typing

import log
import telnet

class Router:
    def __init__(self, name: str, asn: int, a_s: AS, host, port, id: str = "", write:bool =False):
        self.name: str = name
        self.asn: int = asn
        self.a_s: AS = a_s
        self.host: str = host
        self.port: str = port
        self.write: bool = write

        self.is_border: bool = False

        self.interfaces: dict[str, list[str]] = {
            "Loopback0":[],
            "g1/0": [],
            "g2/0": [],
            "g3/0": [],
            "g4/0": []
        }

        if id == "":
            self.id: str = self.name[1:]
        else:
            self.id: str = id

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


class AS:
    def __init__(self, asn: int, internal_protocol: str):
        self.asn: int = asn
        self.internal_protocol: str = internal_protocol
        
        self.routers: dict[str, Router] = {}

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