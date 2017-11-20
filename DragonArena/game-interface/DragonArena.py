import json
import sys
from random import randint

settings = json.load(open('../settings.json'))

DRAGON = settings["dragon"]["symbol"]  # Used to identify a dragon
PLAYER = settings["player"]["symbol"]  # Used to identify a knight/player
EMPTY = 0  # Used to identify an empty grid piece


class Creature:
    """The base class for all creatures in DragonArena"""

    def __init__(self, name, x_pos, y_pos, hp, ap):
        self.name = name
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.max_hp = hp
        self.curr_hp = hp
        self.ap = ap

    def take_hit(self, dmg):
        self.curr_hp -= dmg

    def deal_dmg(self, opponent):
        opponent.take_hit(self.ap)

    def is_alive(self):
        return self.curr_hp > 0

    def get_max_hp(self):
        return self.max_hp

    def get_hp(self):
        return self.curr_hp

    def get_location(self):
        return {'x': self.x_pos, 'y': self.y_pos}

    def get_name(self):
        return self.name


class Knight(Creature):
    """Knight class, would be controlled by player"""

    def __init__(self, x_pos, y_pos, x_max, y_max):
        player_settings = settings["player"]
        hp = randint(player_settings["hp"]["min"], player_settings["hp"]["max"])
        ap = randint(player_settings["ap"]["min"], player_settings["ap"]["max"])
        Creature.__init__(self, "Knight", x_pos, y_pos, hp, ap)
        self.x_max = x_max
        self.y_max = y_max

    # TODO: create move method

    def move_up(self):
        tmp_y = self.y_pos - 1
        self.y_pos = tmp_y if tmp_y > 0 else 0

    def move_down(self):
        tmp_y = self.y_pos + 1
        self.y_pos = tmp_y if tmp_y < self.y_max else self.y_pos

    def move_left(self):
        tmp_x = self.x_pos - 1
        self.x_pos = tmp_x if tmp_x > 0 else 0

    def move_right(self):
        tmp_x = self.x_pos + 1
        self.x_pos = tmp_x if tmp_x < self.x_max else self.x_pos

    # only Knights have ap public.
    def get_ap(self):
        return self.ap


class Dragon(Creature):
    """Dragon class"""

    def __init__(self, x_pos, y_pos):
        dragon_settings = settings["dragon"]
        hp = randint(dragon_settings["ap"]["min"], dragon_settings["ap"]["max"])
        ap = randint(dragon_settings["hp"]["min"], dragon_settings["hp"]["max"])
        Creature.__init__(self, "Dragon", x_pos, y_pos, hp, ap)


class World:
    """The class containing the world the players and dragons fight in"""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.creatures = []
        self.grid = [[EMPTY for x in range(width)] for y in range(height)]

    def insert_player(self, x, y, x_max, y_max):
        self.grid[x][y] = PLAYER
        self.creatures.append(Knight(x, y, x_max, y_max))

    def insert_dragon(self, x, y):
        self.grid[x][y] = DRAGON
        self.creatures.append(Dragon(x, y))

    def remove(self, x, y):
        self.grid[x][y] = EMPTY

    def loc_taken(self, x, y):
        return self.grid[x][y] == DRAGON or self.grid[x][y] == PLAYER

    def draw(self):
        for x in range(0, self.width):
            for y in range(0, self.height):
                sys.stdout.write('%s ' % self.grid[x][y])
            print ''

        sys.stdout.flush()


class DragonArena:
    """The main game class"""

    def __init__(self, dragons, worlds, map_width, map_height):
        '''# ??
         why do we need to store these as values? The state needs to storee Knights
         and Dragons (in lists or something probably). so why do we need to store 'no_of_knights'?
         we could just use len(knight_list) and avoid inconsistencies
         '''
        self.no_of_dragons = dragons
        self.no_of_knights = 0  # initially 0 knights
        self.no_of_worlds = worlds
        self.map_width = map_width
        self.map_height = map_height

        self.worlds = [World(self.map_width, self.map_height) for i in range(self.no_of_worlds)]

    def start(self):
        # create Dragons in each world
        for world in self.worlds:
            for i in range(0, self.no_of_dragons):
                self._place_dragon(world)

    def spawn_random_knights(self, knights):
        # create Knights in each world
        for world in self.worlds:
            for i in range(0, knights):
                self.place_knight(world)

    def place_knight(self, world):
        while True:
            rand_x = randint(0, self.map_width - 1)
            rand_y = randint(0, self.map_height - 1)
            if not world.loc_taken(rand_x, rand_y):
                world.insert_player(rand_x, rand_y, self.map_width, self.map_height)
                break

    def _place_dragon(self, world):
        while True:
            rand_x = randint(0, self.map_width - 1)
            rand_y = randint(0, self.map_height - 1)
            if not world.loc_taken(rand_x, rand_y):
                world.insert_dragon(rand_x, rand_y)
                break

    def draw_worlds(self):
        """
        Draw all worlds to screen
        :return:
        """
        # this can be done better, but had only terminal at the time so ye
        for world in self.worlds:
            world.draw()

    def draw_world(self, index):
        """
        Draw world with specific index to screen
        :param index: Index in worlds to draw to screen
        :return:
        """
        world = self.worlds[index]
        world.draw()
