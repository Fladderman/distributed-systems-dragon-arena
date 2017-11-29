import time
import sys
import os
import messaging
import protected
import random
sys.path.insert(1, os.path.join(sys.path[0], '../game-interface'))
from DragonArenaNew import Creature, Knight, Dragon, DragonArena


class Player:
    def __init__(self):
        pass

class TickingPlayer(Player):
    """
    Bogus player class that just spams request. solely for testing
    """

    @staticmethod
    def main_loop(protected_dragon_arena, my_id):
        assert isinstance(protected_dragon_arena,
                          protected.ProtectedDragonArena)
        print('ticking player main loop')
        # has self._game_state_copy
        try:
            while True:  # while game.playing
                time.sleep(random.random())
                yield messaging.M_R_HEAL(my_id, my_id)
        finally:
            # clean up generator
            return


class HumanPlayer(Player):
    """
    main_loop() is a generator that `yield`s request messages.
        (client outgoing thread is calling and will forward yielded messages)
    the game is over then the generator returns
    """

    @staticmethod
    def main_loop(protected_dragon_arena, my_id):
        assert isinstance(protected_dragon_arena,
                          protected.ProtectedDragonArena)
        # TODO implement. look at BotPlayer for inspiration
        raise NotImplemented


def manhattan_distance(loc1, loc2):
    return abs(loc1[0] - loc2[0]) + abs(loc1[1] - loc2[1])


class BotPlayer(Player):
    @staticmethod

    def _choose_action_return_message(da, my_id):
        must_heal =\
            filter(lambda k: k.get_hp() / float(k.max_hp()) < 0.5,
                   da.heal_candidates(my_id))
        if must_heal:
            return messaging.M_R_HEAL(my_id, must_heal[0])
        can_attack = da.attack_candidates(my_id)
        if can_attack:
            return messaging.M_R_ATTACK(my_id, can_attack[0])
        dragon_locations = da.get_dragon_locations()
        my_loc = da.get_location(my_id)

        dist_with_loc = \
            map(lambda x: (manhattan_distance(my_loc, x), x),
                dragon_locations)

        # sort in place based on distance
        dist_with_loc.sort(key=lambda x: x[0])

        # continue later

        # ?????
        # TODO code unfinished? You may need this :
        # `yield messaging.M_R_MOVE(my_id, coord)`


    def main_loop(protected_dragon_arena, my_id):
        assert isinstance(protected_dragon_arena,
                          protected.ProtectedDragonArena)
        print('bot player main loop')
        # has self._game_state_copy
        try:
            while True:  # while game.playing    # Roy: And I'm not dead?
                time.sleep(0.5)
                with protected_dragon_arena as da:
                    choice = self._choose_action_return_message(da, my_id)
                # lock released, `with` expired
                yield choice
        finally:
            # clean up generator
            return
