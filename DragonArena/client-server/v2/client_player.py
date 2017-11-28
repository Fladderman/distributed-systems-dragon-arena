import time, messaging
import protected_queue, protected_game_state

class Player:
    def __init__(self):
        pass


class HumanPlayer(Player):
    def main_loop(self, req_q, protected_game_state):
        assert isinstance(req_q, protected_queue.ProtectedQueue)
        assert isinstance(req_q, protected_game_state.ProtectedGameState)

        print('human player main loop')
        # has self._game_state_copy
        while True: # while game.playing
            time.sleep(0.5)



class BotPlayer(Player):
    def main_loop(self, req_q, protected_game_state):
        assert isinstance(req_q, protected_queue.ProtectedQueue)
        assert isinstance(req_q, protected_game_state.ProtectedGameState)

        print('bot player main loop')
        # has self._game_state_copy
        while True: # while game.playing
            time.sleep(0.5)
            req_q.push(messaging.M_PING)
