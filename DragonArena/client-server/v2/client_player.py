import time, messaging
import protected_queue

class Player:
    def __init__(self):
        pass

    def setup(self, game_state_copy):
        self._game_state_copy = game_state_copy

    def main_loop(self, request_channel):
        raise NotImplementedError


class HumanPlayer(Player):
    def main_loop(self, req_q):
        assert isinstance(req_q, protected_queue.ProtectedQueue)

        print('human player main loop')
        # has self._game_state_copy
        while True: # while game.playing
            time.sleep(0.5)



class BotPlayer(Player):
    def main_loop(self, req_q):
        assert isinstance(req_q, protected_queue.ProtectedQueue)

        print('bot player main loop')
        # has self._game_state_copy
        while True: # while game.playing
            time.sleep(0.5)
            req_q.push(messaging.M_PING)
