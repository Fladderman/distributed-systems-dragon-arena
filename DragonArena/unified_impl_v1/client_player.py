import time
import messaging
import protected
import das_game_settings
import random
from drawing import ascii_draw
from DragonArenaNew import Direction


class Player:
    pass


class TickingPlayer(Player):
    """ Bogus player class that just spams request. solely for testing
    """

    @staticmethod
    def main_loop(protected_dragon_arena, my_id):
        assert isinstance(protected_dragon_arena,
                          protected.ProtectedDragonArena)
        print('ticking player main loop')
        try:
            while True:  # while game.playing
                print('tick')
                time.sleep(random.random())
                yield messaging.M_R_HEAL(my_id)
        except GeneratorExit:
            # clean up generator
            return

class FuzzerPlayer(Player):
    """ main_loop() is a generator that `yield`s request messages.
        (client outgoing thread is calling and will forward yielded messages)
    the game is over then the generator returns
    """

    @staticmethod
    def main_loop(protected_dragon_arena, my_id):
        assert isinstance(protected_dragon_arena,
                          protected.ProtectedDragonArena)
        print('fuzzer player main loop')
        print('my id', my_id)
        # has self._game_state_copy
        try:
            while True:  # TODO: while game.playing    # Roy: And I'm not dead?
                time.sleep(random.uniform(0.0001, das_game_settings.server_min_tick_time))
                with protected_dragon_arena as da:
                    try:
                        x = random.choice(range(4))
                        if x == 0:
                            choice = messaging.M_R_ATTACK()

                    except Exception as e:
                        choice = None
                        debug_print("FUZZER CRASHED WHEN DECIDING", e)
                # `with` expired. dragon arena unlocked
                if choice is not None:
                    yield choice
        except GeneratorExit:
            # clean up generator
            return

class HumanPlayer(Player):
    """ main_loop() is a generator that `yield`s request messages.
        (client outgoing thread is calling and will forward yielded messages)
    the game is over then the generator returns
    """

    @staticmethod
    def main_loop(protected_dragon_arena, my_id):
        assert isinstance(protected_dragon_arena,
                          protected.ProtectedDragonArena)
        # TODO implement. look at BotPlayer for inspiration
        raise NotImplemented


class BotPlayer(Player):
    @staticmethod
    def _choose_action_return_message(da, my_id):
        """ given the dragon arena 'da', make a decision on the next
        action for the bot to take. formulate this as a Message (request) from
        the set {MOVE, ATTACK, HEAL} and return it as your action
        """

        if not da._id_exists(my_id) or da.is_dead(my_id):
            return None

        must_heal = filter(lambda k: k.get_hp() / float(k.max_hp()) < 0.5,
                           da.heal_candidates(my_id))
        if must_heal:
            return messaging.M_R_HEAL(must_heal[0])
        can_attack = da.attack_candidates(my_id)
        if can_attack:
            return messaging.M_R_ATTACK(can_attack[0])
        # else get moving

        dragon_locations = da.get_dragon_locations()
        if not dragon_locations:
            return None
        # print('dragon_locations' , dragon_locations)

        def manhattan_distance(loc1, loc2):
            return abs(loc1[0] - loc2[0]) + abs(loc1[1] - loc2[1])

        def min_distance_to_dragon(loc):
            return min(map(lambda z: manhattan_distance(loc, z),
                           dragon_locations))

        my_loc = x, y = da.get_location(my_id)
        current_min = min_distance_to_dragon(my_loc)
        # print('current_min', current_min)
        adjacent = filter(lambda z: da.is_valid_location(z[0]),
                          [((x+1, y), Direction.DOWN), ((x-1, y), Direction.UP),
                           ((x, y+1), Direction.RIGHT), ((x, y-1), Direction.LEFT)])
        # print('adjacent' , adjacent)
        #MUST be non-empty
        improving = \
            filter(lambda z: min_distance_to_dragon(z[0]) < current_min,
                   adjacent)
        # print('improving', improving)
        available_improving =\
            filter(lambda z: not da.is_occupied_location(z[0]), improving)
        pick_from = available_improving if available_improving else improving
        if not pick_from:
            return None
        direction = random.choice(pick_from)[1]

        return messaging.M_R_MOVE(direction)

    @staticmethod
    def main_loop(protected_dragon_arena, my_id):
        assert isinstance(protected_dragon_arena,
                          protected.ProtectedDragonArena)
        print('bot player main loop')
        print('my id', my_id)
        # has self._game_state_copy
        st = das_game_settings.server_min_tick_time
        try:
            while True:  # TODO: while game.playing    # Roy: And I'm not dead?
                time.sleep(random.uniform(st*0.8, st/0.8))
                with protected_dragon_arena as da:
                    if das_game_settings.client_visualizer:
                        ascii_draw(da, me=my_id)
                    try:
                        choice = BotPlayer._choose_action_return_message(da, my_id)
                    except Exception as e:
                        choice = None
                        debug_print("BOT CRASHED WHEN DECIDING", e)
                # `with` expired. dragon arena unlocked
                if choice is not None:
                    yield choice
        except GeneratorExit:
            # clean up generator
            return
