from .models import *

def compute_ip_address(router_a: Router, router_b: Router, ip_address: IPVersion):
    if router_a.asn == router_b.asn: # Same AS
        if ip_address == IPVersion.IPV4:
            return ipv4_link_intra_as(router_a.name, router_b.name, router_a.asn)
        else:
            return ipv6_link_intra_as(router_a.name, router_b.name, router_a.asn)

    else: # Different AS
        if ip_address == IPVersion.IPV4:
            return ipv4_link_inter_as(router_a.name, router_a.asn, router_b.name, router_b.asn)
        else:
            return ipv6_link_inter_as(router_a.name, router_a.asn, router_b.name, router_b.asn)


def ipv4_link_intra_as(router_a_name: str, router_b_name:str, num_as):
    id_a = int(''.join(filter(str.isdigit, router_a_name)))
    id_b = int(''.join(filter(str.isdigit, router_b_name)))

    low, high = sorted([id_a, id_b])
    prefix = f"{num_as}.0.{low}{high}"

    return f"{prefix}.{id_a} 255.255.255.0", f"{prefix}.{id_b} 255.255.255.0"

def ipv4_link_inter_as(router_a_name: str, asn_a: int, router_b_name: str, asn_b: int):
    id_a = int(''.join(filter(str.isdigit, router_a_name)))
    id_b = int(''.join(filter(str.isdigit, router_b_name)))

    low_as, high_as = sorted([asn_a, asn_b])
    low_id, high_id = sorted([id_a, id_b])
    prefix = f"{low_as}{high_as}.0.{low_id}{high_id}"

    return f"{prefix}.{id_a} 255.255.255.0", f"{prefix}.{id_b} 255.255.255.0"


def ipv6_link_intra_as(router_a_name: str, router_b_name:str, num_as):
    id_a = int(''.join(filter(str.isdigit, router_a_name)))
    id_b = int(''.join(filter(str.isdigit, router_b_name)))

    low, high = sorted([id_a, id_b])
    prefix = f"fd{num_as}:{low}{high}::"

    return f"{prefix}{id_a}/64", f"{prefix}{id_b}/64"

def ipv6_link_inter_as(router_a_name: str, asn_a: int, router_b_name: str, asn_b: int):
    id_a = int(''.join(filter(str.isdigit, router_a_name)))
    id_b = int(''.join(filter(str.isdigit, router_b_name)))

    low_as, high_as = sorted([asn_a, asn_b])
    low_id, high_id = sorted([id_a, id_b])
    prefix = f"fd{low_as}{high_as}:{low_id}{high_id}::"

    return f"{prefix}{id_a}/64", f"{prefix}{id_b}/64"

def compute_loopback_address(router_name: str, asn: int, ip_version: IPVersion):
    router_id = int(''.join(filter(str.isdigit, router_name)))

    if ip_version == IPVersion.IPV4:
        return f"{asn}.0.0.{router_id} 255.255.255.255"
    else:
        return f"fd{asn}::{router_id}/128"

def remove_ipv4_mask(ipv4):
    return ipv4.split(" ")[0]

def remove_ipv6_mask(ipv6):
    """Supprime le /64 si présent (obligatoire pour BGP neighbor)"""
    return ipv6.split("/")[0]