import server
import sys

if __name__ == '__main__':
    try:
        assert len(sys.argv) == 2
        server_id = int(sys.argv[1])
    except:
        raise 'please provide 1 arg, an integer of the server index'

    serv_0 = server.Server(server_id)
    serv_0.main_loop()
