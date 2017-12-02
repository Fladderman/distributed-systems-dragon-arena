import server
import sys

if __name__ == '__main__':
    try:
        assert len(sys.argv) == 3
        server_id = int(sys.argv[1])
        is_starter = sys.argv[2] == 'True'
    except:
        raise RuntimeError('usage:\n\t$ python2 server_start.py [server_id] [is_starter]')

    serv_0 = server.Server(server_id, is_starter)
    serv_0.main_loop()
