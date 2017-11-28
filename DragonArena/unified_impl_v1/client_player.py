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


@staticmethod
def manhattan_distance(loc1, loc2):
    return abs(loc1[0] - loc2[0]) + abs(loc1[1] - loc2[1])

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

    # chris, integrate this plz
    # suppose: my_id and da are respectively the bot's knight id
    # and its da object
    my_id = (1, 2)
    da = DragonArena(2, 2, 2)

    while True:  # while I'm alive and the game is running
        must_heal = filter(lambda k: k.get_hp() / float(k.max_hp()) < 0.5,
                           da.heal_candidates(my_id))
        if must_heal:
            da.heal(my_id, must_heal[0])  # send this as request to server
        else:
            can_attack = da.attack_candidates(my_id)
            if can_attack:
                da.attack(my_id, can_attack[0])  # send this as req to server
            else:
                dragon_locations = da.get_dragon_locations()
                my_loc = da.get_location(my_id)

                # to continue, manhattan distance is defined up already




