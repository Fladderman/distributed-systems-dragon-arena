import itertools
import random
import das_game_settings as dgs
import hashlib
from sys import maxsize


class Direction:
    RIGHT = 0
    UP = 1
    LEFT = 2
    DOWN = 3


class Creature:
    def __init__(self, name, identifier, max_hp, curr_hp, ap):
        self._name = name
        self._identifier = identifier
        self._max_hp = max_hp
        self._curr_hp = curr_hp
        self._ap = ap

    def is_attacked_by(self, other):
        self._curr_hp = max(self._curr_hp - other.get_ap(), 0)

    def is_alive(self):
        return self._curr_hp > 0

    def get_max_hp(self):
        return self._max_hp

    def get_hp(self):
        return self._curr_hp

    def get_name(self):
        return self._name

    def get_ap(self):
        return self._ap

    def get_identifier(self):
        return self._identifier

    def serialize(self):
        return [isinstance(self, Knight),
                list(self._identifier),
                self._max_hp,
                self._curr_hp,
                self._ap]

    @staticmethod
    def deserialize(o):
        if o[0]:  # knight
            return Knight(tuple(o[1]), o[2], o[3], o[4])
        else:
            return Dragon(tuple(o[1]), o[2], o[3], o[4])


class Knight(Creature):
    def __init__(self, identifier, max_hp=None, curr_hp=None, ap=None):
        max_hp = max_hp if max_hp is not None else \
            random.randint(dgs.knight_hp_bounds[0],
                           dgs.knight_hp_bounds[1])
        curr_hp = curr_hp if curr_hp is not None else max_hp
        ap = ap if ap is not None else \
            random.randint(dgs.knight_ap_bounds[0],
                           dgs.knight_ap_bounds[1])
        Creature.__init__(self, "Knight", identifier, max_hp, curr_hp, ap)

    def is_healed_by(self, other):
        self._curr_hp = min(self._curr_hp + other.get_ap(), self._max_hp)


class Dragon(Creature):
    def __init__(self, identifier, max_hp=None, curr_hp=None, ap=None):
        max_hp = max_hp if max_hp is not None else \
            random.randint(dgs.dragon_hp_bounds[0],
                           dgs.dragon_hp_bounds[1])
        curr_hp = curr_hp if curr_hp is not None else max_hp
        ap = ap if ap is not None else \
            random.randint(dgs.dragon_ap_bounds[0],
                           dgs.dragon_ap_bounds[1])
        Creature.__init__(self, "Dragon", identifier, max_hp, curr_hp, ap)


class DragonArena:
    def __init__(self, no_of_dragons, map_width, map_height):
        # allow at least one knight to be spawned
        assert no_of_dragons < map_width * map_height

        self.game_over = False

        self.key = random.randint(0, 100000)

        self._tick = 1

        self._DRAGON = -1

        self._no_of_dragons = no_of_dragons
        self._map_width = map_width
        self._map_height = map_height

        # Generate all valid locations. Used in some private methods.
        self._locations = set(itertools.product(range(map_height),
                                                range(map_width)))

        # Set up dictionaries.
        self._creature2loc = dict()
        self._loc2creature = dict()
        self._id2creature = dict()

        # ^ Only these three dictionaries need to be managed at all times.
        # The mappings below are derived.

        # Added for uniformity in naming:
        self._creature2id = lambda x: x.get_identifier()
        # Compositions:
        self._loc2id = lambda x: self._creature2id(self._loc2creature[x])
        self._id2loc = lambda x: self._creature2loc[self._id2creature[x]]

        # Small annoyance: e.g. self._creature2loc is a dictionary, while
        # self._creature2id is a function. So given a Knight knight1,
        # one must write (note parentheses):
        #   self._creature2loc[knight1]
        #   self._creature2id(knight1)
        # Also for example:
        #   self._creature2loc.get_keys() is defined
        #   self._creature2id.get_keys() is not defined
        # This requires some mindfulness in the implementation, but it is okay
        # if one programs using an IDE.

        # Included purely for efficiency reasons. Termination checks are
        # frequent, and without these fields, every time the creature2loc
        # dictionary keys need to be filtered.
        self._no_of_living_dragons = 0
        self._no_of_living_knights = 0

        # !!!
        # Note that function new_game() has to be called!

    # BELOW ALL PRIVATE METHODS

    @staticmethod
    def format_id(identifier):
        return "{{{type}|{id}}}".format(type=identifier[0], id=identifier[1])

    def _all_knights_are_dead(self):
        return self._no_of_living_knights == 0

    def _all_dragons_are_dead(self):
        return self._no_of_living_dragons == 0

    def _get_occupied_locations(self):
        return self._loc2creature.keys()

    def _get_available_locations(self):
        return self._locations - set(self._get_occupied_locations())

    def _get_random_available_location(self):
        # this ensures that concurrent servers generate the same
        # 'random' location
        seed = self._tick * (self._no_of_living_knights + 1)
        rng = random.Random(seed)
        return rng.sample(sorted(list(self._get_available_locations())), 1)[0]

    def _is_occupied_by_knight(self, location):
        return self.is_occupied_location(location) and \
               isinstance(self._loc2creature[location], Knight)

    def _is_occupied_by_dragon(self, location):
        return self.is_occupied_location(location) and \
               isinstance(self._loc2creature[location], Dragon)

    def _id_exists(self, identifier):
        return identifier in self._id2creature.keys()

    def _id_is_fresh(self, identifier):
        return not self._id_exists(identifier)

    def is_dead(self, identifier):
        return self._id2creature[identifier] is None

    def _is_alive(self, identifier):
        return not self.is_dead(identifier)

    # horizontal or vertical (our notion of distance), maxsize otherwise
    def _distance(self, id1, id2):
        loc1 = self._id2loc(id1)
        loc2 = self._id2loc(id2)

        x_diff = abs(loc1[0] - loc2[0])
        y_diff = abs(loc1[1] - loc2[1])

        if x_diff > 0 and y_diff > 0:  # not in a vertical or horizontal line
            return maxsize

        return max(x_diff, y_diff)

    def _is_in_healing_range(self, id1, id2):
        return self._distance(id1, id2) <= 5

    def _is_in_attack_range(self, id1, id2):
        return self._distance(id1, id2) <= 2

    # helper method for the actual move methods
    def _move_help(self, next_location, direction, knight_id):
        # in case of bad request, throw an error
        if not self._id_exists(knight_id):
            raise RuntimeError("Can't move! The knight with id ", knight_id, 'Doesnt exist!')

        # knight might have died previously, ok
        if self.is_dead(knight_id):
            return ("Knight {id} wants to move {dir}, but it is dead."
                    ).format(id=DragonArena.format_id(knight_id),
                             dir=direction)

        at = self._id2loc(knight_id)
        to = next_location(at)

        if not self.is_valid_location(to):
            return ("Knight {id} wants to move {dir} from {at}, but it is "
                    "blocked by the arena boundary."
                    ).format(id=DragonArena.format_id(knight_id),
                             dir=direction, at=at)

        if self.is_occupied_location(to):
            blocker = self._loc2creature[to]
            return ("Knight {id} wants to move {dir} from {at}, but it is "
                    "blocked by {blocker_name} {blocker_id}."
                    ).format(id=DragonArena.format_id(knight_id),
                             dir=direction, at=at,
                             blocker_name=blocker.get_name(),
                             blocker_id=DragonArena.format_id(
                                 blocker.get_identifier()))

        # ok to move
        knight = self._id2creature[knight_id]
        self._creature2loc[knight] = to  # knight -> at becomes knight -> to
        self._loc2creature.pop(at)  # remove at -> knight
        self._loc2creature[to] = knight  # add to -> knight
        return ("Knight {id} moves {dir} from {at} to {to}."
                ).format(id=DragonArena.format_id(knight_id),
                         dir=direction, at=at, to=to)

    # BELOW ALL PUBLIC/INTERFACING METHODS

    # This one is used by Zak for his drawing engine, NOT the calling server.
    def get_sorted_grid_including_creatures(self):
        sorted_locations = sorted(list(self._locations))

        def get_creature(x): return self._loc2creature[x] \
            if x in self._loc2creature.keys() else x
        return map(get_creature, sorted_locations)

    # The calling server can at any time (re)start the game. The ID space is
    # cleaned, all knights are removed, and no_of_dragons are randomly put on
    # the map again.
    def new_game(self):
        self._tick = 0

        self.game_over = False

        self.key = random.randint(0, 10000)

        # Initialize all dragon objects.
        dragons = [Dragon((self._DRAGON, i))
                   for i in xrange(self._no_of_dragons)]

        # Create dictionary containing <dragon> : <location>
        self._creature2loc = dict(zip(dragons, random.sample(self._locations,
                                                             len(dragons))))
        # Create the inverse (<location> : <dragon>}
        self._loc2creature = dict(zip(self._creature2loc.values(),
                                      self._creature2loc.keys()))
        # create dictionary containing <id> : <dragon>
        self._id2creature = dict(map(lambda x: (x.get_identifier(), x),
                                     dragons))

        self._no_of_living_dragons = self._no_of_dragons
        self._no_of_living_knights = 0

        opening_message = ["A NEW GAME STARTS.",
                           "The battlefield has size {h}x{w}.".format(
                               h=self._map_height, w=self._map_width),
                           "{n} dragons have been spawned.".format(
                               n=self._no_of_dragons),
                           ]

        for dragon, location in self._creature2loc.iteritems():
            spawn_msg = ("Dragon {id} has been spawned at location "
                         "{location}, with {hp} hp and {ap} ap."
                         ).format(id=DragonArena.format_id(
                                    dragon.get_identifier()),
                                  location=location,
                                  hp=dragon.get_hp(),
                                  ap=dragon.get_ap()
                                  )
            opening_message.append(spawn_msg)

        return "\n".join(opening_message)

    def game_is_full(self):
        return self._no_of_living_dragons + self._no_of_living_knights == \
               self._map_height * self._map_width

    # The calling server can spawn a knight.
    #   Very important: server will have to propose an ID here.
    # The reason is that servers will concurrently modify their local
    # DragonArena object, and then they will merge their states.
    # See Google docs document Identifier Protocol.
    def spawn_knight(self, proposed_id):
        assert self._id_is_fresh(proposed_id)
        assert not self.game_is_full()

        seed = self._tick * (self._no_of_living_knights + 1) + \
            proposed_id[0] + proposed_id[1]

        knight = Knight(proposed_id)
        spawn_at = self._get_random_available_location()

        self._creature2loc[knight] = spawn_at
        self._loc2creature[spawn_at] = knight
        self._id2creature[proposed_id] = knight

        self._no_of_living_knights += 1

        return ("Knight {id} spawns at location {loc} with {hp} hp and "
                "{ap} ap."
                ).format(id=DragonArena.format_id(proposed_id),
                         loc=spawn_at, hp=knight.get_hp(),
                         ap=knight.get_ap())

    # If a client disconnects, the server can manually kill off a knight.
    # ONLY THAT PURPOSE
    def kill_knight(self, knight_id):
        assert self._id_exists(knight_id)

        knight = self._id2creature[knight_id]
        loc = self._creature2loc[knight]

        self._creature2loc.pop(knight)
        self._loc2creature.pop(loc)
        self._id2creature[knight_id] = None

        self._no_of_living_knights -= 1

        end_game_msg = ""

        if self._all_knights_are_dead():
            self.game_over = True
            end_game_msg = ("GAME OVER: "
                            "All knights are dead. The dragons win!")

        return ("Knight {id} at location {loc} committed suicide."
                "{end_game_msg}"
                ).format(id=DragonArena.format_id(knight_id),
                         loc=loc, end_game_msg=end_game_msg)

    # Move methods. Whether the ID is valid is checked in the helper method.
    def move_up(self, knight_id):
        return self._move_help(lambda l: (l[0] - 1, l[1]), "up", knight_id)

    def move_down(self, knight_id):
        return self._move_help(lambda l: (l[0] + 1, l[1]), "down", knight_id)

    def move_left(self, knight_id):
        return self._move_help(lambda l: (l[0], l[1] - 1), "left", knight_id)

    def move_right(self, knight_id):
        return self._move_help(lambda l: (l[0], l[1] + 1), "right", knight_id)

    # Assumption: servers call this using knight_id for id1 and dragon_id
    # for id2. This object calls this the other way around to process a round
    # of dragon: see self.let_dragons_attack() below.
    def attack(self, id1, id2):
        assert self._id_exists(id1)
        assert self._id_exists(id2)

        name1 = "Dragon" if id1[0] == self._DRAGON else "Knight"
        name2 = "Dragon" if id2[0] == self._DRAGON else "Knight"

        # ensure attack is valid
        assert name1 != name2

        # check for death

        if self.is_dead(id1):
            return ("{name1} {id1} wants to attack {name2} {id2}, but {name1} "
                    "{id1} is dead."
                    ).format(name1=name1, id1=DragonArena.format_id(id1),
                             name2=name2, id2=DragonArena.format_id(id2))

        if self.is_dead(id1):
            return ("{name1} {id1} wants to attack {name2} {id2}, but {name1} "
                    "{id1} is dead."
                    ).format(name1=name1, id1=DragonArena.format_id(id1),
                             name2=name2, id2=DragonArena.format_id(id2))

        # check for range

        if not self._is_in_attack_range(id1, id2):
            return ("{name1} {id1} wants to attack {name2} {id2}, but {name2} "
                    "{id2} is out of range."
                    ).format(name1=name1, id1=DragonArena.format_id(id1),
                             name2=name2, id2=DragonArena.format_id(id2))

        # ok to attack

        creature1 = self._id2creature[id1]
        creature2 = self._id2creature[id2]

        old_hp = creature2.get_hp()
        creature2.is_attacked_by(creature1)
        new_hp = creature2.get_hp()

        death_notification = ""

        end_game_msg = ""

        if not creature2.is_alive():
            loc2 = self._creature2loc[creature2]
            self._creature2loc.pop(creature2)
            self._loc2creature.pop(loc2)
            self._id2creature[id2] = None

            death_notification = "\n{name2} {id2} dies.".format(
                name2=name2, id2=DragonArena.format_id(id2))

            if isinstance(creature2, Knight):
                self._no_of_living_knights -= 1

                if self._all_knights_are_dead():
                    self.game_over = True
                    end_game_msg = ("GAME OVER: "
                                    "All knights are dead. The dragons win!")
            else:
                self._no_of_living_dragons -= 1

                if self._all_dragons_are_dead():
                    self.game_over = True
                    end_game_msg = ("GAME OVER: "
                                    "All dragons are dead. The knights win!")

        return ("{name1} {id1} attacks {name2} {id2} for {dmg} damage, "
                "reducing its hp from "
                "{old_hp} to {new_hp}.{death_notification}{end_game_msg}"
                ).format(name1=name1, id1=DragonArena.format_id(id1),
                         name2=name2, id2=DragonArena.format_id(id2),
                         dmg=creature1.get_ap(), old_hp=old_hp, new_hp=new_hp,
                         death_notification=death_notification,
                         end_game_msg=end_game_msg)

    # Allows the calling server to process a heal.
    def heal(self, id1, id2):
        assert self._id_exists(id1)
        assert self._id_exists(id2)

        # ensure heal is valid
        assert id1[0] != self._DRAGON and id2[0] != self._DRAGON

        # check for death

        if self.is_dead(id1):
            return ("Knight {id1} wants to heal Knight {id2}, but Knight "
                    "{id1} is dead."
                    ).format(id1=DragonArena.format_id(id1),
                             id2=DragonArena.format_id(id2))

        if self.is_dead(id2):
            return ("Knight {id1} wants to heal Knight {id2}, but Knight "
                    "{id2} is dead."
                    ).format(id1=DragonArena.format_id(id1),
                             id2=DragonArena.format_id(id2))

        # check for range

        if not self._is_in_healing_range(id1, id2):
            return ("Knight {id1} wants to heal Knight {id2}, but Knight "
                    "{id2} is out of range."
                    ).format(id1=DragonArena.format_id(id1),
                             id2=DragonArena.format_id(id2))

        # ok to heal

        creature1 = self._id2creature[id1]
        creature2 = self._id2creature[id2]

        old_hp = creature2.get_hp()
        creature2.is_healed_by(creature1)
        new_hp = creature2.get_hp()

        return ("Knight {id1} heals Knight {id2} for {points} points, "
                "restoring its hp from "
                "{old_hp} to {new_hp}."
                ).format(id1=DragonArena.format_id(id1),
                         id2=DragonArena.format_id(id2),
                         points=creature1.get_ap(),
                         old_hp=old_hp, new_hp=new_hp)

    def attack_candidates(self, identifier):  # used by bot and for dragons
        attacker_loc = self._id2loc(identifier)
        x = attacker_loc[0]
        y = attacker_loc[1]
        predicate = self._is_occupied_by_knight if \
            identifier[0] == self._DRAGON else self._is_occupied_by_dragon
        target_loc = filter(predicate,
                            [(x - 2, y), (x - 1, y), (x + 1, y), (x + 2, y),
                             (x, y - 2), (x, y - 1), (x, y + 1), (x, y + 2)]
                            )

        return map(self._loc2id, target_loc)

    def heal_candidates(self, knight_id):  # used by bot
        healer_loc = self._id2loc(knight_id)
        x = healer_loc[0]
        y = healer_loc[1]
        coordinates = [(x + i, y) for i in xrange(5, -6)] + \
                      [(x, y + i) for i in xrange(5, -6)]
        coords = filter(self._is_occupied_by_knight, coordinates)
        return map(self._loc2id, coords)

    def get_location(self, identifier):  # used by bot
        return self._id2loc(identifier)

    def get_knights(self):
        return filter(lambda x: isinstance(x, Knight),
                      self._creature2loc.keys())

    def get_dragons(self):
        return filter(lambda x: isinstance(x, Dragon),
                      self._creature2loc.keys())

    def get_dragon_locations(self):  # used by bot
        return map(lambda d: self._creature2loc[d], self.get_dragons())

    def is_valid_location(self, location):  # used by bot and internally
        return 0 <= location[0] < self._map_height and \
               0 <= location[1] < self._map_width

    def is_occupied_location(self, location):  # used by bot and internally
        return location in self._get_occupied_locations()

    # Allows the calling server to process a round of dragon attacks.
    def let_dragons_attack(self):
        dragon_ids = map(self._creature2id, self.get_dragons())

        # target selection algorithm.
        # atm just picks the first (at least deterministic)
        def select_target(candidates): return candidates[0]

        log_messages = []

        for dragon_id in dragon_ids:
            k = dgs.ticks_per_dragon_attack

            # don't let all dragons attack in the same tick
            if (self._tick + dragon_id[1]) % k == 0:
                knight_ids = self.attack_candidates(dragon_id)

                if knight_ids:
                    knight_id = select_target(knight_ids)
                    log_messages.append(self.attack(dragon_id, knight_id))

        return "\n".join(log_messages)

    def was_ever_a_knight(self, identifier):
        return self._id_exists(identifier) and identifier[0] >= 0

    def is_knight(self, identifier):  # by server
        return self._id_exists(identifier) and \
               isinstance(self._id2creature[identifier], Knight)

    def is_dragon(self, identifier):  # by server
        return self._id_exists(identifier) and \
               isinstance(self._id2creature[identifier], Dragon)

    # Below: serialization for networking

    def serialize(self):
        serial_creature2loc = map(lambda t: [t[0].serialize(), list(t[1])],
                                  self._creature2loc.items())
        # When deserializing, we will want to reconstruct id2loc.
        # It consists of:
        #   1. living creature IDs that map to their loc
        #   2. dead creature IDs that map to None
        # 1 can be reconstructed from serial_creature2loc
        # hence we only need to send the IDs of dead creatures in addition
        dead_creature_ids = map(lambda t: list(t[0]),
                                filter(lambda t: t[1] is None,
                                       self._id2creature.items()))
        return (self._no_of_dragons,
                self._map_width,
                self._map_height,
                serial_creature2loc,
                dead_creature_ids,
                self._tick,
                self.key,
                self.game_over
                )

    @staticmethod
    def deserialize(o):
        no_of_dragons = o[0]
        map_width = o[1]
        map_height = o[2]
        serial_creature2loc = o[3]
        dead_creature_ids = o[4]
        tick = o[5]
        key = o[6]
        game_over = o[7]

        creature2loc_list = \
            map(lambda l: (Creature.deserialize(l[0]), tuple(l[1])),
                serial_creature2loc)

        creature2loc = dict(creature2loc_list)

        id2creature = dict(map(lambda t: (t[0].get_identifier(), t[0]),
                               creature2loc_list))

        for identifier in dead_creature_ids:
            id2creature[tuple(identifier)] = None

        arena = DragonArena(no_of_dragons, map_width, map_height)
        arena.restore(creature2loc, id2creature, tick, key, game_over)

        return arena

    # called exclusively by deserialize in the DragonArena class!
    def restore(self, creature2loc, id2creature, tick, key, game_over):
        self._tick = tick
        self.key = key
        self.game_over = game_over
        self._creature2loc = creature2loc
        self._id2creature = id2creature

        self._loc2creature = dict(zip(self._creature2loc.values(),
                                      self._creature2loc.keys()))

        self._no_of_living_dragons = 0
        self._no_of_living_knights = 0

        for creature in self._creature2loc.keys():
            if isinstance(creature, Dragon):
                self._no_of_living_dragons += 1
            else:
                self._no_of_living_knights += 1

    def get_tick(self):
        return self._tick

    def increment_tick(self):
        self._tick += 1

    def get_winner(self):
        if self._no_of_living_dragons == 0:
            return "knights"
        else:
            return "dragons"

    # https: // cyan4973.github.io / xxHash /
    def get_hash(self):
        h = hashlib.md5()
        for identifier in sorted(self._id2creature.keys()):
            h.update(str(identifier))
            if self._is_alive(identifier):
                h.update(str(self._id2creature[identifier].serialize()))
                h.update(str(self._id2loc(identifier)))
        h.update(str(self._tick))
        h.update(str(self.game_over))
        h.update(str(self.key))
        return h.hexdigest()[:8]
