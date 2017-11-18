#!/usr/local/bin/python2

# server
import socket
import time
import threading
import sys
import json

# Import settings from settings file
settings = json.load(open('settings.json'))
BACKLOG = settings["server"]["backlog"]
MAX_CLIENTS = settings["game"]["max_players"]
PORTS = settings["server"]["ports"]

PROMPT_SYMBOL = "->"

socket.setdefaulttimeout(20)  # Accept timeout in sec


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

        # Opens socket for server
        self.server_socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)

    def run(self):
        """
        Accept clients and add them to the client list
        :return:
        """

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

        host = socket.gethostname()
        self.server_socket.bind((host, PORTS[0]))

        # Queue max 5 requests
        self.server_socket.listen(BACKLOG)

        while not self._stopped():
            # Establish a connection
            try:
                client_socket, addr = self.server_socket.accept()
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

        self._thread_stopped()

    def stop(self):
        # For a graceful shutdown, set flag
        self._stop_event.set()

    def _stopped(self):
        """
        Use to check whether a graceful shutdown has been requested
        :return:
        """
        return self._stop_event.is_set()

    def _thread_stopped(self):
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
        prompt = prompt.lower()
        if prompt == "stop":
            if self.thread.isAlive():
                print "Stopping thread..."
                self.thread.stop()
            else:
                print "No thread running"

        elif prompt == "force-stop":
            # Still needs to be implemented!
            return
            if self.thread.isAlive():
                print "Force stopping thread..."
                #self.thread.stop(force=True)
            else:
                print "No thread running"

        elif prompt == "start":
            if self.thread is None:
                self._start_server()
            elif self.thread.isAlive():
                print "Thread already running"
            else:
                self._start_server()

        elif prompt == "exit":
            if not self.thread.isAlive():
                exit(0)
            else:
                print "Still accepting clients"


print "type 'start' to start accepting clients and 'stop' to stop accepting clients gracefully (waits for timeout)"

server = Server()
server.start()
