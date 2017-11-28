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

    def main_loop(self, protected_dragon_arena, my_id):
        assert isinstance(protected_dragon_arena, protected.ProtectedGameState)
        print('human player main loop')
        # has self._game_state_copy
        while True: # while game.playing
            time.sleep(0.5)
            with protected_dragon_arena as game_state:
                # lock acquired
                # read game state. decide what to do
                pass
            #lock released
            yield messaging.M_PLAYER_REQ_DUMMY


def manhattan_distance(loc1, loc2):
    return abs(loc1[0] - loc2[0]) + abs(loc1[1] - loc2[1])

class BotPlayer(Player):
    def main_loop(self, protected_dragon_arena, my_id):
        assert isinstance(protected_dragon_arena, protected.ProtectedGameState)
        print('bot player main loop')
        # has self._game_state_copy
        while True:  # while game.playing    # Roy: And I'm not dead?
            time.sleep(0.5)
            with protected_dragon_arena as da:
                must_heal = filter(lambda k: k.get_hp() / float(k.max_hp()) < 0.5,
                                   da.heal_candidates(my_id))
                if must_heal:
                    yield messaging.M_R_HEAL(my_id, must_heal[0])
                else:
                    can_attack = da.attack_candidates(my_id)
                    if can_attack:
                        yield messaging.M_R_ATTACK(my_id, can_attack[0])
                    else:
                        dragon_locations = da.get_dragon_locations()
                        my_loc = da.get_location(my_id)

                        dist_with_loc = \
                            map(lambda x: (manhattan_distance(my_loc, x), x),
                                dragon_locations)

                        # sort in place based on distance
                        dist_with_loc.sort(key=lambda x: x[0])

                        # continue later

                        #?????
                        # TODO code unfinished? You may need this : `yield messaging.M_R_MOVE(my_id, coord)`

            #lock released, `with` expired
