#!/usr/local/bin/python2

import socket
import time
import json
import sys
import os


# Import settings from settings file
settings = json.load(open('../settings.json'))

# Select what ports to connect to, should late be changed to IPs of server nodes
# combined with port number
ports = settings["server"]["ports"]


class Client():
    def __init__(self):
        self.ip = None
        self.port = None

    def start(self):
        self.ip, self.port = self._get_server()

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_socket.connect((self.ip, self.port))
        except socket.error:
            # Connection failed, could be because server is down,
            # SHould not happen since we just pinged server

            print "Unable to connect to server"
            exit(1)

        # Receive no more than 1024 bytes
        msg = client_socket.recv(1024)

        if msg == "ACK":
            # Server accepted us!
            while True:
                #  TODO THIS IS WHERE ALL CLIENT LOGIC NEEDS TO HAPPEN
                time.sleep(2)
        else:
            # Server reject
            print "Server NACK received"
            exit(1)

        client_socket.close()

    def _get_server(self):
        """
        Ping all servers and return the IP and Port number
        of the best one
        :return:
        """
        # Best time measures best round trip time to server
        bestTime = sys.maxint

        # TODO Does not work yet!!!
        """
        for ip in settings["server"]["ips"]:
            hostname = ip
            response = os.system("ping -c 1 " + hostname)

            # TODO store best time values
            port = settings["server"]["ports"][0]
            bestIp = socket.gethostname()  # CHANGE LATER
        """
        # Get local machine name
        host = socket.gethostname()
        port = settings["server"]["ports"][0]

        return host, port


if __name__ == "__main__":
    client = Client()

    client.start()
