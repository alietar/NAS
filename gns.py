# Ajouter : link_style: Optional[Any] = None dans la library gns3fy

from gns3fy import gns3fy, Project, Node, Link

import datetime
import time


class GnsProject:
    def __init__(self, ip="http://localhost", port=3080, name="Test project") -> None:
        self.name = name
        self.routers = {}

        self.server = gns3fy.Gns3Connector(f"{ip}:{str(port)}")
        self.lab = gns3fy.Project(name=self.name, connector=self.server)


    def create_new(self, auto_recover=False):
        if auto_recover:
            if self.server.get_project(self.name) is not None:
                self.recover_existing()

                return
        self.lab.create()


    def recover_existing(self):
        self.lab.get()
        

    def open(self):
        self.lab.open()


    def close(self):
        self.lab.close()


    def create_router(self, name="Router", model="c7200", auto_recover=False, x=0, y=0):
        if auto_recover:
            for node in self.lab.nodes:
                if node.name == name:
                    self.recover_router(name, model)

                    return
        
        router = Node(
            project_id=self.lab.project_id,
            connector=self.server,
            name=name,
            template=model,
            x=x,
            y=y
        )

        router.create()

        self.routers[name] = router


    def recover_router(self,  name="Router", model="c7200"):
        router = Node(
            project_id=self.lab.project_id,
            connector=self.server,
            name=name,
            template=model
        )

        router.get()

        self.routers[name] = router


    def get_router_interface(self, router_name, port_name):
        if port_name is None:
            print("ERROR Please give at least one type of name")

            return None
        
        for port in self.routers[router_name].ports:
            if port["name"] == port_name or port["short_name"] == port_name:
                return {"adapter": port["adapter_number"], "port": port["port_number"]}
            

    def create_link(self, r1_name, r1_port_name, r2_name, r2_port_name):
        r1_interface = self.get_router_interface(r1_name, r1_port_name)
        r2_interface = self.get_router_interface(r2_name, r2_port_name)

        nodes = [
            dict(node_id=self.routers[r1_name].node_id,
                 adapter_number=r1_interface["adapter"],
                 port_number=r1_interface["port"]),
            dict(node_id=self.routers[r2_name].node_id,
                 adapter_number=r2_interface["adapter"],
                 port_number=r2_interface["port"]),
        ]
        
        link = Link(project_id=self.lab.project_id, connector=self.server, nodes=nodes)
        link.create()


    def get_router_port(self, router_name):
        return self.routers[router_name].console