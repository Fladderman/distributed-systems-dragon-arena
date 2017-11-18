#!/usr/local/bin/python2

# server
import socket
import time
import threading
import sys

PORTS = [9999, 9998, 9997, 9996, 9995]
BACKLOG = 5
MAX_CLIENTS = 100
PROMPT_SYMBOL = "->"

socket.setdefaulttimeout(2)  # SHOULD BE MORE, set to 5sec to make testing easier


class ServerConnectedThread(threading.Thread):
    """
    Thread that accepts clients and adds them to the
    inputted client_set in the __init__ method
    """
    def __init__(self, name, client_set, max, prompt_symbol):
        threading.Thread.__init__(self)
        self._stop_event = threading.Event()
        self.max = max
        self.name = name
        self.connected_clients = client_set
        self.prompt_symbol = prompt_symbol

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        """
        Accept clients and add them to the client list
        :return:
        """

        # Opens socket for server
        serversocket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)

        host = socket.gethostname()

        """ ---- Code from Rink to use multiple ports, but is blocking. Commented out for now ----
        for port in PORTS:
            print("Starts for loop for ports")
            try:
                serversocket.bind((host, port))
                print("Now using port %s" % port)
                break
            except socket.error as e:
                print("Trying next port")
        """

        serversocket.bind((host, PORTS[0]))

        # Queue max 5 requests
        serversocket.listen(BACKLOG)

        while not self.stopped():
            # Establish a connection
            try:
                client_socket, addr = serversocket.accept()
            except socket.timeout:
                self._print("Accept timeout")
                # Start over
                continue

            # Sleep for 1 second to emulate round trip times
            time.sleep(1)
            if len(self.connected_clients) < self.max:
                self.connected_clients.add(addr)
                client_socket.send("ACK")
                self._print("Accepted a connection from %s" % str(addr))
            else:
                client_socket.send("NACK")
                self._print("Declined a connection from %s" % str(addr))
            client_socket.close()

        self._print("Stopped thread")
        print "{}: ".format(self.prompt_symbol),
        sys.stdout.flush()

    def _print(self, value):
        print "{}".format(value)
        sys.stdout.flush()


class Server:
    """
    Main server class, handles user commands and starts/stops receiving clients
    """
    def __init__(self):
        self.thread = None
        self.connected_clients = set()

    def _start_server(self):
        """
        Start receiving clients in a new thread
        :return:
        """
        t = ServerConnectedThread("incoming_client_connections", self.connected_clients, MAX_CLIENTS, PROMPT_SYMBOL)
        self.thread = t
        t.start()

    def start(self):
        while True:
            prompt = str(raw_input("{}: ".format(PROMPT_SYMBOL)))

            self._handle_command(prompt)

    def _handle_command(self, prompt):
        """
        Handle user input
        :return:
        """
        if prompt == "stop":
            print "Stopping thread..."
            self.thread.stop()
        elif prompt == "start":
            self._start_server()
        elif prompt == "exit":
            exit(0)


print "type 'start' to start accepting clients and 'stop' to stop accepting clients"

server = Server()
server.start()
