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
from .protocol.links import link_config

from .utils import structures

### CLI Arguments
@click.command()
@click.argument('intentfile', type=click.Path(exists=True, readable=True), default="./intents/intent_2_AS_OSPF_RIP.json")
def main(intentfile):
    console.print("[b][blue]Cisco routers configuration tool[/b][/blue]")

    ### --- Intent file reading --- ###
    intents, gns_config, ip_version, use_gnsfy = structures.read_intents(intentfile)
    as_list, routers = structures.parse_routers_as(intents)

    ### --- Config making --- ###
    ## Basic router config
    for router in routers.values():
        router.append_cmds(commands.base_router_config(router.name))
        router.append_cmds(commands.enable_community()) # Mandatory for communities

    ## Interface, opsf, rip and eBGP, setup
    link_config(routers, as_list, intents, gns_config, ip_version)

    ## Enable BGP on every router
    for name, r in routers.items():
        r.append_cmds(commands.bgp_config(r.id, r.asn, ip_version))

    ibgp_config(routers, as_list, intents, gns_config, ip_version)
    apply_vpn(routers, as_list, intents)


    ### --- GNS --- ###
    if use_gnsfy:
        ## Project opening
        g = gns_utils.open_gns(gns_config)
    
        for router in routers.values():
            ## Router creation
            if gns_config.get("create_routers", False):
                gns_utils.create_router(router, g, intents, gns_config.get("arrange"))

            ## Ports
            if gns_config.get("auto_fetch_router_infos", False):
                router.port = gns_utils.fetch_ports(router, g)
                router.host = gns_config.get("ip", "127.0.0.1")

        ## Links creation
        if gns_config.get("create_links", False):
            gns_utils.create_links(intents, g)

        ## Start all router on GNS
        with console.status("[blue] Starting routers (GNS)...") as status:
            for name in routers.keys():
                g.routers[name].start()

        log.success("Started routers (GNS)")

        with console.status("[blue] Waiting 10s for routers to start") as status:
            time.sleep(10)


    ### Telnet sending
    telnet.write_configs_parallel(routers)
    
    console.print("\n[b][green]Finished![/b][/green]")


if __name__ == "__main__":
    main()