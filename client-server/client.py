# client.py
import socket
import time

# hard coded ports for now, should be IP later
ports = [9999, 9998]

# get local machine name
host = socket.gethostname()

bestTime = float("inf")
bestPort = 0

for port in ports:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(port)
    #t0 and t1 are measuring round trip time
    t0 = time.time()

    # connection to hostname on the port.
    s.connect((host, port))
    # Receive no more than 1024 bytes
    msg = s.recv(1024)
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
