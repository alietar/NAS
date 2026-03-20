import telnetlib3.telnetlib as telnetlib
import time
import log

INTERVAL_BETWEEN_CMD: float = 0.03

def run_on_router(cmds, host, port):
    routerSocket = RouterSocket(host=host, port=port)

    for cmd in cmds:
        routerSocket.run(cmd)

    routerSocket.close()


class RouterSocket:
    def __init__(self, host="localhost", port=0) -> None:
        try:
            self.tn = telnetlib.Telnet(host, port)
        except Exception as exp:
            log.fatal_error(f"Can't connect to router, check the given host and port, check if the router is started", exp)
        
        self.tn.write(b"\r\n")
        self.tn.write(b"\r\n")
        self.tn.write(b"\r\n")
        self.emptyChannel()
        

    def run(self, command):
        # print(f"-> {command}")
        self.tn.write(command.encode("ascii")+b"\r\n")
        time.sleep(INTERVAL_BETWEEN_CMD)
        # self.emptyChannel()


    def close(self):
        self.tn.close()

    def emptyChannel(self):
        while self.tn.read_very_eager() != b"":
            self.tn.write(b"\r\n")
            pass