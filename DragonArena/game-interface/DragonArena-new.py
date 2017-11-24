import itertools # for product
import json
import sys
from random import randint, shuffle, sample

settings = json.load(open('../settings.json'))

'''
DRAGON = settings["dragon"]["symbol"]  # Used to identify a dragon
PLAYER = settings["player"]["symbol"]  # Used to identify a knight/player
EMPTY = 0  # Used to identify an empty grid piece
'''

# IDs will be added later, and code modified throughout

class Creature:
    def __init__(self, name, max_hp, ap):
        self.name = name
        self.max_hp = max_hp
        self.curr_hp = max_hp
        self.ap = ap

    def take_hit(self, dmg):
        self.curr_hp = max(self.curr_hp - dmg, 0)

    def get_healed(self, amount):
        self.curr_hp = min(self.curr_hp + amount, self.max_hp)

    def is_alive(self):
        return self.curr_hp > 0

    def get_max_hp(self):
        return self.max_hp

    def get_hp(self):
        return self.curr_hp

    def get_name(self):
        return self.name

    # Roy: Before, ap of dragons could not be requested. But in principle
    # everything must be inspectable, since servers must send complete game
    # states to other servers. I suggest we keep things simple and also just
    # send entire game states to clients.

    def get_ap(self):
        return self.ap


# Now that movement is handled in the World class, the only difference between
# a Knight and Dragon object are the properties with which they are initialized.

class Knight(Creature):
    def __init__(self):
        player_settings = settings["player"]
        max_hp = randint(player_settings["hp"]["min"], player_settings["hp"]["max"])
        ap = randint(player_settings["ap"]["min"], player_settings["ap"]["max"])
        Creature.__init__(self, "Knight", max_hp, ap)

class Dragon(Creature):
    def __init__(self):
        dragon_settings = settings["dragon"]
        max_hp = randint(dragon_settings["ap"]["min"], dragon_settings["ap"]["max"])
        ap = randint(dragon_settings["hp"]["min"], dragon_settings["hp"]["max"])
        Creature.__init__(self, "Dragon", max_hp, ap)

class DragonArena:
    def __init__(self, no_of_dragons, map_width, map_height):
        # generate all valid locations. used in some private methods
        self.locations = set(itertools.product(range(map_height), range(map_width)))

        # initialize all dragon objects
        dragons = [Dragon() for _ in range(no_of_dragons)]

        # with (int) IDs, use e.g.:
        # dragons = [Dragon(-i) for i in range(no_of_dragons)]
        #
        # if servers then never propose negative IDs, we guarantee that
        # player and dragon IDs remain disjoint at all times.

        # set up dicts. note that objects only exist as keys in this dict when
        # alive: maintaining a separate list means more redundancy.
        # also effectively assigns a random cell to each dragon

        shuffled_locations = shuffle(list(self.locations))
        self.dragon2loc = dict(zip(dragon, shuffled_locations))
        self.knight2loc = dict()

        # entities will be cleared from dictionary when they die.
        # maybe it's good to maintain a graveyard, so we can
        # distinguish between requests for dead entities (ok, can happen
        # in same tick) and entities that do not exist (some error)
        self.graveyard = set()

    def _get_occupied_locations(self):
        return set(self.dragon2loc.values() + self.knight2loc.values())

    def _get_available_locations(self):
        return self.locations - self._get_occupied_locations()

    def _get_random_available_location(self):
        return sample(self._get_available_locations(), 1)[0]

    def _is_valid(self, location):
        return location in locations

    def _is_occupied(self, location):
        return location in self._get_occupied_locations()

    # note: this is private!
    # log messages need to be more descriptive, using ids (later) and direction
    def _move(self, nextLocation, direction, knight):
        at = knight2loc[knight]
        to = nextLocation(at)

        if not self._is_valid(to):
            return "[DAS] Knight hit boundary."
        elif self._is_occupied(to):
            return "[DAS] Knight was blocked by another player or dragon."
        else:
            knight2loc[knight] = to
            return "[DAS] Knight moved from " + str(at) + " to " + str(to) + "."

    # BELOW ALL INTERFACING METHODS!
    # integrate ids later

    # Very important: server will have to propose an id here.
    # The reason is that servers will concurrently modify their local
    # DragonArena object, and then they will merge their states.
    # This can cause id collisions if a e.g. an object-local counter is used.is
    # Suggestion: each server proposes ids with a server-unique prefix.
    def spawn_knight(self): # parameter once ids are added: proposed_id
        knight = Knight()
        spawn_at = self._get_random_available_location()

        self.knight2loc[knight] = spawn_at

        return (knight, "[DAS] Spawned a knight at location " + str(spawn_at) + ".")

    def moveUp(self, knight):
        self._move(lambda x,y : (x+1, y), "up", knight)

    def moveDown(self, knight):
        self._move(lambda x,y : (x-1, y), "down", knight)

    def moveLeft(self, knight):
        self._move(lambda x,y : (x, y-1), "left", knight)

    def moveRight(self, knight):
        self._move(lambda x,y : (x, y+1), "right", knight)