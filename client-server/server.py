import socket
import time

serversocket = socket.socket(
    socket.AF_INET, socket.SOCK_STREAM)

host = socket.gethostname()

ports = [9999, 9998, 9997, 9996, 9995]
finalPort = 0
maxClients = 1
currentClients = set()

for port in ports:
    print("Starts for loop")
    try:
        serversocket.bind((host, port))
        print("Now using port %s" %port)
        break
    except socket.error as e:
        print("Trying next port")

serversocket.listen(5)

while True:
    # establish a connection
    clientsocket,addr = serversocket.accept()
    time.sleep(1)
    if(len(currentClients) < maxClients ):
        currentClients.add(addr)
        clientsocket.send("ACK")
        print("Accepted a connection from %s" % str(addr))
    else:
        clientsocket.send("NACK")
        print("Declined a connection from %s" % str(addr))
    clientsocket.close()
