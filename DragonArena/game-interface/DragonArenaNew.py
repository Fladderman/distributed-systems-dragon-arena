import json
import itertools
import random
from sys import maxsize

settings = json.load(open('../settings.json'))

# I make one simplifying assumption: servers never submit dragon ids


class Creature:
    def __init__(self, name, max_hp, ap, identifier):
        self.name = name
        self.max_hp = max_hp
        self.curr_hp = max_hp
        self.ap = ap
        self.identifier = identifier

    def take_hit(self, dmg):
        self.curr_hp = max(self.curr_hp - dmg, 0)

    def attacks(self, other):
        other.curr_hp = max(other.curr_hp - self.ap, 0)

    def is_alive(self):
        return self.curr_hp > 0

    def get_max_hp(self):
        return self.max_hp

    def get_hp(self):
        return self.curr_hp

    def get_name(self):
        return self.name

    # Roy: Before, ap of dragons could not be requested. But in principle
    # everything must be retrievable, since servers must send complete game
    # states to other servers. I suggest we keep things simple and also just
    # send entire game states to clients.

    def get_ap(self):
        return self.ap

    def get_identifier(self):
        return self.identifier


class Knight(Creature):
    def __init__(self, identifier):
        player_settings = settings["player"]
        max_hp = random.randint(player_settings["hp"]["min"],
                                player_settings["hp"]["max"])
        ap = random.randint(player_settings["ap"]["min"],
                            player_settings["ap"]["max"])
        Creature.__init__(self, "Knight", max_hp, ap, identifier)

    def heals(self, other):
        other.curr_hp = min(other.curr_hp + self.ap, other.max_hp)


class Dragon(Creature):
    def __init__(self, identifier):
        dragon_settings = settings["dragon"]
        max_hp = random.randint(dragon_settings["ap"]["min"],
                                dragon_settings["ap"]["max"])
        ap = random.randint(dragon_settings["hp"]["min"],
                            dragon_settings["hp"]["max"])
        Creature.__init__(self, "Dragon", max_hp, ap, identifier)


class DragonArena:
    def __init__(self, no_of_dragons, map_width, map_height):
        self.map_width = map_width
        self.map_height = map_height

        # generate all valid locations. used in some private methods
        self.locations = set(itertools.product(range(map_height),
                                               range(map_width)))

        # initialize all dragon objects
        # use negative ints for dragons, >= 0 for players
        dragons = [Dragon(-(i+1)) for i in range(no_of_dragons)]

        # create dictionary containing {dragon: location}
        self.creature2loc = dict(zip(dragons, random.sample(self.locations,
                                                            len(dragons))))
        # create the inverse {location: dragon}
        self.loc2creature = dict(zip(self.creature2loc.values(),
                                     self.creature2loc.keys()))
        # create dictionary containing {id: dragon}
        self.id2creature = dict(map(lambda x: (x.get_identifier(), x),
                                    dragons))

        # ^ only these three dicts need to be managed at all times
        # the ones below are derived.
        # (also note that a loc l is free iff not l in loc2creature)

        # added for uniformity in naming:
        self.creature2id = lambda x: x.get_identifier()
        # compositions:
        self.loc2id = lambda x: self.creature2id(self.loc2creature[x])
        self.id2loc = lambda x: self.creature2loc[self.id2creature[x]]

    # BELOW ALL PRIVATE METHODS

    def _get_living_dragon_ids(self):
        return map(self.creature2id,
                   filter(lambda x: isinstance(x, Dragon),
                          self.creature2loc.keys())
                   )

    def _get_living_knight_ids(self):
        return map(self.creature2id,
                   filter(lambda x: isinstance(x, Knight),
                          self.creature2loc.keys())
                   )

    def _get_occupied_locations(self):
        return self.loc2creature.keys()

    def _get_available_locations(self):
        return self.locations - set(self._get_occupied_locations())

    def _get_random_available_location(self):
        return random.sample(self._get_available_locations(), 1)[0]

    def _is_valid_location(self, location):
        return 0 <= location[0] < self.map_height and \
               0 <= location[1] < self.map_width

    def _is_occupied_location(self, location):
        return location in self._get_occupied_locations()

    def _is_occupied_by_knight(self, location):
        return self._is_occupied_location(location) and \
               isinstance(self.loc2creature[location], Knight)

    def _id_exists(self, identifier):
        return identifier in self.id2creature.keys()

    def _id_is_fresh(self, identifier):
        return not self._id_exists(identifier)

    def _is_dead(self, identifier):
        return not self.id2creature[identifier].is_alive()

    def _is_alive(self, identifier):
        return self.id2creature[identifier].is_alive()

    # horizontal or vertical (our notion of distance), maxsize otherwise
    def _distance(self, id1, id2):
        loc1 = self.id2loc(id1)
        loc2 = self.id2loc(id2)

        x_diff = abs(loc1[0] - loc2[0])
        y_diff = abs(loc1[1] - loc2[1])

        if x_diff > 0 and y_diff > 0:  # not in a vertical or horizontal line
            return maxsize

        return max(x_diff, y_diff)

    def _is_in_healing_range(self, id1, id2):
        return self._distance(id1, id2) <= 5

    def _is_in_attack_range(self, id1, id2):
        return self._distance(id1, id2) <= 2

    def _get_knight_ids_in_attack_range(self, dragon_id):
        dragon_loc = self.id2loc(dragon_id)
        x = dragon_loc[0]
        y = dragon_loc[1]
        knight_loc = filter(self._is_occupied_by_knight,
                            [(x - 2, y), (x - 1, y), (x + 1, y), (x + 2, y),
                             (x, y - 2), (x, y - 1), (x, y + 1), (x, y + 2)]
                            )
        return map(lambda loc: self.loc2id(loc), knight_loc)

    def _move_help(self, next_location, direction, knight_id):
        # in case of bad request, throw an error
        assert(self._id_exists(knight_id))

        # knight might have died previously, ok
        if self._is_dead(knight_id):
            return "Knight {id} wants to move {dir}, but it is dead."

        at = self.id2loc(knight_id)
        to = next_location(at)

        if not self._is_valid_location(to):
            return ("Knight {id} wants to move {dir} from {at}, but it is "
                    "blocked by the arena boundary."
                    ).format(id=knight_id, dir=direction, at=at)

        if self._is_occupied_location(to):
            blocker = self.loc2creature[to]
            return ("Knight {id} wants to move {dir} from {at}, but it is "
                    "blocked by {blocker_name} {blocker_id}."
                    ).format(id=knight_id, dir=direction, at=at,
                             blocker_name=blocker.get_name(),
                             blocker_id=blocker.get_identifier())

        # ok to move
        knight = self.id2creature[knight_id]
        self.creature2loc[knight] = to  # knight -> at becomes knight -> to
        self.loc2creature.pop(at)  # remove at -> knight
        self.loc2creature[to] = knight  # add to -> knight
        return "Knight {id} moves {dir} from {at} to {to}.".format(
            id=knight_id, dir=direction, at=at, to=to)

    # BELOW ALL INTERFACING METHODS

    def get_sorted_grid_including_creatures(self):
        sorted_locations = sorted(list(self.locations))

        def get_creature(x): return self.loc2creature[x] \
            if x in self.loc2creature.keys() else x
        return map(get_creature, sorted_locations)

    # Very important: server will have to propose an id here.
    # The reason is that servers will concurrently modify their local
    # DragonArena object, and then they will merge their states.
    # This can cause id collisions if a e.g. an object-local counter is used.
    # Suggestion: each server proposes ids with a server-unique prefix.
    def spawn_knight(self, proposed_id):
        assert (self._id_is_fresh(proposed_id))

        knight = Knight(proposed_id)
        spawn_at = self._get_random_available_location()

        self.creature2loc[knight] = spawn_at
        self.loc2creature[spawn_at] = knight
        self.id2creature[proposed_id] = knight

        return "Knight {id} spawns at location {loc}".format(
            id=proposed_id, loc=spawn_at)

    def move_up(self, knight_id):
        self._move_help(lambda x, y: (x+1, y), "up", knight_id)

    def move_down(self, knight_id):
        self._move_help(lambda x, y: (x-1, y), "down", knight_id)

    def move_left(self, knight_id):
        self._move_help(lambda x, y: (x, y-1), "left", knight_id)

    def move_right(self, knight_id):
        self._move_help(lambda x, y: (x, y+1), "right", knight_id)

    # servers call this using knight_id for id1 and dragon_id for id2
    # this object calls this the other way around for dragon attacks
    def attack(self, id1, id2):
        assert(self._id_exists(id1))
        assert(self._id_exists(id2))

        creature1 = self.id2creature[id1]
        creature2 = self.id2creature[id2]

        # ensure attack is valid
        assert creature1 != creature2

        name1 = creature1.get_name()
        name2 = creature2.get_name()

        # check for death

        if self._is_dead(id1):
            return ("{name1} {id1} wants to attack {name2} {id2}, but {name1} "
                    "{id1} is dead."
                    ).format(name1=name1, id1=id1, name2=name2, id2=name2)

        if self._is_dead(id2):
            return ("{name1} {id1} wants to attack {name2} {id2}, but {name2} "
                    "{id2} is already dead."
                    ).format(name1=name1, id1=id1, name2=name2, id2=name2)

        # check for range

        if not self._is_in_attack_range(id1, id2):
            return ("{name1} {id1} wants to attack {name2} {id2}, but {name2} "
                    "{id2} is out of range."
                    ).format(name1=name1, id1=id1, name2=name2, id2=name2)

        # ok to attack

        old_hp = creature2.get_hp()
        creature1.attacks(creature2)
        new_hp = creature2.get_hp()

        death_notification = ""

        if creature2.is_dead():
            loc2 = self.creature2loc[creature2]
            self.creature2loc.pop(creature2)
            self.loc2creature.pop(loc2)
            death_notification = " {name2} {id2} dies.".format(name2=name2,
                                                               id2=id)

        return ("{name1} {id1} attacks {name2} {id2}, reducing its hp from "
                "{old_hp} to {new_hp}.{death_notification}"
                ).format(name1=name1, id1=id1, name2=name2, id2=id2,
                         old_hp=old_hp, new_hp=new_hp,
                         death_notification=death_notification)

    def heal(self, id1, id2):
        assert(self._id_exists(id1))
        assert(self._id_exists(id2))

        creature1 = self.id2creature[id1]
        creature2 = self.id2creature[id2]

        # ensure heal is valid
        assert(isinstance(creature1, Knight) and isinstance(creature2, Knight))

        # check for death

        if self._is_dead(id1):
            return ("Knight {id1} wants to heal Knight {id2}, but Knight "
                    "{id1} is dead."
                    ).format(id1=id1, id2=id2)

        if self._is_dead(id2):
            return ("Knight {id1} wants to heal Knight {id2}, but Knight "
                    "{id2} is dead."
                    ).format(id1=id1, id2=id2)

        # check for range

        if not self._is_in_healing_range(id1, id2):
            return ("Knight {id1} wants to heal Knight {id2}, but Knight "
                    "{id2} is out of range."
                    ).format(id1=id1, id2=id2)

        # ok to heal

        old_hp = creature2.get_hp()
        creature1.heals(creature2)
        new_hp = creature2.get_hp()

        return ("Knight {id1} heals Knight {id2}, restoring its hp from "
                "{old_hp} to {new_hp}."
                ).format(id1=id1, id2=id2, old_hp=old_hp, new_hp=new_hp)

    # Will improve this later. Target selection should actually not be done in
    # parallel as it is done now. Rather, it should be interleaved with attacks
    # so that dragon actions never lag behind on state.
    def let_dragons_attack(self):
        dragon_ids = self._get_living_dragon_ids()

        # target selection algorithm.
        # atm just picks the first (at least deterministic)
        def select_target(candidates): return candidates[0]

        log_messages = []

        for dragon_id in dragon_ids:
            target_ids = self._get_knight_ids_in_attack_range(dragon_id)
            if target_ids:
                target_id = select_target(target_ids)
                log_messages.append(self.attack(dragon_id, target_id))

        return "\n".join(log_messages)
