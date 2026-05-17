### Native libraries
import time

### Added libraries
import click
from rich.pretty import pprint

### Own libraries
from .router_connector import gns_utils
from . import commands 
from .utils.ip_utils import *
from .utils import log
from .utils.log import console
from .utils.models import *

from .protocol.mpls_vpn.vpn import apply_vpn
from .protocol.bgp.ibgp import ibgp_config
from .protocol.links import link_config, configure_loopbacks

from .utils import parser

### CLI Arguments
@click.command()
@click.argument('intentfile', type=click.Path(exists=True, readable=True), default="./intents/intent_2_AS_OSPF_RIP.json")
@click.option('-d', '--dry-run', is_flag=True)
@click.option('-s', '--show-commands', is_flag=True)
def main(intentfile, dry_run, show_commands):
    console.print("[b][blue]Cisco routers configuration tool[/b][/blue]")

    ### --- Intent file reading --- ###
    intents, gns_config, ip_version, use_gnsfy = parser.parse_intents(intentfile)
    as_list, routers = parser.parse_routers_as(intents)

    ### --- Config making --- ###
    ## Basic router config
    for router in routers.values():
        router.append_cmds(commands.base_router_config(router.name))
        router.append_cmds(commands.enable_community()) # Mandatory for communities
    
    
    for link in intents["links"]:
        r_a: Router = routers[link["from"]]
        r_b: Router = routers[link["to"]]
        interface_a: str = link["interface_from"]
        interface_b: str = link["interface_to"]

        r_a.interfaces[interface_a] = Interface(interface_a)
        r_b.interfaces[interface_b] = Interface(interface_b)
    
        r_a.interfaces[interface_a].neighbor_router = r_b
        r_b.interfaces[interface_b].neighbor_router = r_a
    
        if r_a.asn == r_b.asn: # Same as
            r_a.interfaces[interface_a].is_internal = True
            r_b.interfaces[interface_b].is_internal = True

        else: # Different as
            r_a.is_border = True
            r_b.is_border = True
    
    apply_vpn(routers, as_list, intents)

    ## Interface, opsf, rip and eBGP, setup
    link_config(routers, as_list, intents, gns_config, ip_version)

    ## Enable BGP on every router
    for r in routers.values():
        if r.a_s.bgp_deployement == "border" and not r.is_border:
            continue

        r.append_cmds(commands.bgp_config(r.id, r.asn, ip_version))

    configure_loopbacks(routers, intents, ip_version)
    ibgp_config(routers, as_list, intents, gns_config, ip_version)

 
    if show_commands:
        for router in routers.values():
            log.info(f"Commands on router {router.name}")
            for cmd in router.cmds:
                print(cmd)

    ### --- GNS --- ###
    if not dry_run:
        if use_gnsfy:
            ## Project opening
            g = gns_utils.open_gns(gns_config)
        
            for router in routers.values():
                ## Router creation
                if gns_config.get("create_routers", False):
                    gns_utils.create_router(router, g, intents, gns_config.get("arrange", False))

                ## Ports
                if gns_config.get("auto_fetch_router_infos", False):
                    router.port = gns_utils.fetch_ports(router, g)
                    router.host = gns_config.get("ip", "127.0.0.1")

            ## Links creation
            if gns_config.get("create_links", False):
                gns_utils.create_links(intents, g, routers)

            ## Start all router on GNS
            with console.status("[blue] Starting routers (GNS)...") as status:
                for r in routers.values():
                    g.routers[r.name].start()

            log.success("Started routers (GNS)")

            with console.status("[blue] Waiting 10s for routers to start") as status:
                time.sleep(10)


        ### Telnet sending
        telnet.write_configs_parallel(routers)
    
    console.print("\n[b][green]Finished![/b][/green]")


if __name__ == "__main__":
    main()