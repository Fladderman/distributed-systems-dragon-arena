import threading, time, json, socket
import messaging, das_game_settings

class Client:
    def __init__(self):
        sorted_server_pings = self._ordered_server_list()
        serv_socket = Client.sock_client(ip, port)
        msg = Message(0,0,[])
        messaging.write_msg_to(serv_socket, msg)
        msg = messaging.read_msg_from(serv_socket)
        print(str(msg))
        time.sleep(5.0)


    def _ordered_server_list(self):
        for i, addr in enumerate(das_game_settings.server_addresses):
            sock = sock_client

    '''
    attempts to connect
    '''
    @staticmethod
    def sock_client(ip, port, timeout=2.0):
        assert isinstance(ip, str)
        assert isinstance(port, int)
        assert isinstance(timeout, int) or isinstance(timeout, float)
        try:
            socket.setdefaulttimeout(timeout)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, port))
            return s
        except:
            return None

    def main_loop(self):
        while True:
            pass
