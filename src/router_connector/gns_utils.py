from utils import log, ip_utils
from .gns_project import GnsProject
from .display import router_coords_from_intent

def open_gns(gns_config):
    log.info("Auto config is enabled, connecting to the server... (GNS)")

    try:
        g = GnsProject(name=gns_config["project_name"], ip=gns_config.get("ip", "http://localhost"), port=gns_config.get("port", 3080))
        g.create_new(auto_recover=True)
        g.open()
    
        log.success("Opened/created the project (GNS)")

    except Exception as exp:
        log.fatal_error("Failed to connect to the GNS server", exp)

    return g


def create_links(intents, g):
    for link in intents["links"]:
        log.info(f"Adding link from {link["interface_from"]} on {link["from"]} to {link["interface_to"]} on {link["to"]} (GNS)")
        try:
            g.create_link(link["from"], # Adding link inside GNS
                        link["interface_from"],
                        link["to"],
                        link["interface_to"])
        except Exception as exp:
            log.fatal_error(f"Cannot create link from {link["interface_from"]} on {link["from"]} to {link["interface_to"]} on {link["to"]}, check if the interfaces are not used twice !!", exp)


def fetch_ports(router: ip_utils.Router, g):
    # Getting host and port depending on choosed method,
    # either automaticaly from GNS or with the user's intents

    return g.get_router_port(router.name)


def create_router(router, g, intents={}, arrange: bool|None = False):
    name = router.name

    try:
        log.info(f"Creating/recovering router {name} (GNS)")

        if arrange == "circle":
            g.lab.arrange_nodes_circular()
        if arrange == "by_as":
            router_positions = router_coords_from_intent(
                intents,
                as_radius=400,
                router_radius=80,
                center=(0, 0),
            )

            pos = router_positions.get(name, {"x": 0, "y": 0})
            g.create_router(name=name, auto_recover=True, x=pos["x"], y=pos["y"])
        else:
            g.create_router(name=name, auto_recover=True)

    except Exception as exp:
        log.console.print_exception()
        log.fatal_error("Failed to create/recover the router {name} (GNS)", exp)