# Client
import socket
import time

# Hard coded ports for now, should be IP later (?)
ports = [9999, 9998]

# Get local machine name
host = socket.gethostname()

# Best time measures best round trip time to server
bestTime = float("inf")

# Best port saves what port (later IP) to connect to
bestPort = 0

# Tries all ports available in the array and tries to make a connection
# Measures the time to connect to server and decides on what is the best server
for port in ports:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #t0 and t1 are measuring round trip time
    t0 = time.time()

    # connection to hostname on the port.
    s.connect((host, port))

    # Receive no more than 1024 bytes
    msg = s.recv(1024)

    # Only save best time of server if the server accepts the client
    if(msg == "ACK"):
        t1 = time.time()
        rtt = t1 - t0
        s.close()
        if rtt < bestTime:
            bestTime = rtt
            bestPort = port

s.close()
print("The best RTT was: %s" %bestTime)
print("Chose for port: %s" %bestPort)
