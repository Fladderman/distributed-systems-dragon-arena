import time
import messaging, protected

class Player:
    def __init__(self):
        pass
    def setup(self, req_q, protected_game_state):
        assert isinstance(req_q, protected.ProtectedQueue)
        assert isinstance(protected_game_state, protected.ProtectedGameState)
        self._req_q = req_q
        self._protected_game_state = protected_game_state

class HumanPlayer(Player):
    def main_loop(self):
        assert hasattr(self, '_req_q') and hasattr(self, '_protected_game_state')
        print('human player main loop')
        # has self._game_state_copy
        while True: # while game.playing
            time.sleep(0.5)



class BotPlayer(Player):
    def main_loop(self):
        assert hasattr(self, '_req_q') and hasattr(self, '_protected_game_state')
        print('bot player main loop')
        # has self._game_state_copy
        while True: # while game.playing
            time.sleep(0.5)
            req_q.push(messaging.M_PLAYER_REQ_DUMMY)
