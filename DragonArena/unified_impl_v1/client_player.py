import time, sys, os
import messaging, protected
sys.path.insert(1, os.path.join(sys.path[0], '../game-interface'))
from DragonArenaNew import Creature, Knight, Dragon, DragonArena

class Player:
    def __init__(self):
        pass

class HumanPlayer(Player):
    '''
    main_loop() is a generator that `yield`s request messages.
        (client outgoing thread is calling and will forward yielded messages)
    the game is over then the generator returns
    '''

    def main_loop(self, protected_game_state):
        assert isinstance(protected_game_state, protected.ProtectedGameState)
        print('human player main loop')
        # has self._game_state_copy
        while True: # while game.playing
            time.sleep(0.5)
            with protected_game_state as game_state:
                # lock acquired
                # read game state. decide what to do
                pass
            #lock released
            yield messaging.M_PLAYER_REQ_DUMMY



class BotPlayer(Player):
    def main_loop(self, protected_game_state):
        assert isinstance(protected_game_state, protected.ProtectedGameState)
        print('bot player main loop')
        # has self._game_state_copy
        while True: # while game.playing
            time.sleep(0.5)
            with protected_game_state as game_state:
                print('state locked')
                # lock acquired
                # read game state. decide what to do
                pass
            #lock released
            print('bot yield')
            yield messaging.M_PLAYER_REQ_DUMMY
