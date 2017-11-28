import server
import sys

assert len(sys.argv) == 2

serv_0 = server.Server(int(sys.argv[1]))
serv_0.main_loop()
