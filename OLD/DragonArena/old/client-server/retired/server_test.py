import socket_communications
import json
import thread
# Import settings from settings file
settings = json.load(open('../settings.json'))

# Select what ports to connect to, should late be changed to IPs of server nodes
# combined with port number
ports = settings["server"]["ports"]

server = socket_communications.ServerSocket()

server.accept()

print "server accept ok"
