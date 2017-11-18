# server
import socket
import time

# Opens socket for server
serversocket = socket.socket(
    socket.AF_INET, socket.SOCK_STREAM)

host = socket.gethostname()

# Array of ports that the server is going to try to use. Maybe this should eventually be IPs?
ports = [9999, 9998, 9997, 9996, 9995]

# Number of clients that the server is going to hold in currentClients
maxClients = 1
currentClients = set()

# Verbose method for finding the right port to start on
for port in ports:
    print("Starts for loop")
    try:
        serversocket.bind((host, port))
        print("Now using port %s" %port)
        break
    except socket.error as e:
        print("Trying next port")

# Queue max 5 requests
serversocket.listen(5)

# Responds to clients connecting.
# If the server can accept the client (is not too busy) a ACK is send
# Otherwise a NACK is send
while True:
    # Establish a connection
    clientsocket,addr = serversocket.accept()

    # Sleep for 1 second to emulate round trip times
    time.sleep(1)
    if(len(currentClients) < maxClients ):
        currentClients.add(addr)
        clientsocket.send("ACK")
        print("Accepted a connection from %s" % str(addr))
    else:
        clientsocket.send("NACK")
        print("Declined a connection from %s" % str(addr))
    clientsocket.close()
