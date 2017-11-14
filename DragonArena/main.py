import sys
import pygame
from pygame.locals import *
from random import randint



class Creature:
    """The base class for all creatures in DragonArena"""
    def __init__(self, name, x_pos, y_pos, hp, ap):
        self.name       = name
        self.x_pos      = x_pos
        self.y_pos      = y_pos
        self.max_hp     = hp
        self.curr_hp    = hp
        self.ap         = ap

    def take_hit(self, dmg):
        self.curr_hp -= dmg

    def deal_dmg(self, opponent):
        opponent.take_hit(self.ap)

    def is_alive(self):
        return self.curr_hp > 0

    def get_max_hp(self):
        return self.max_hp

    def get_hp(self):
        return self.hp

    def get_location(self):
        return {'x':self.x_pos, 'y':self.y_pos}

    def get_name(self):
    	return self.name


class Knight(Creature):
    """Knight class, would be controlled by player"""
    def __init__(self, x_pos, y_pos, x_max, y_max):
        hp = randint(10,20)
        ap = randint(1,10)
        super().__init__("Knight", x_pos, y_pos, hp, ap)
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
        hp = randint(50,100)
        ap = randint(5,20)
        super().__init__("Dragon", x_pos, y_pos, hp, ap)


class World:
    """The class containing the world the players and dragons fight in"""
    def __init__(self, width, height):
    	self.width = width
    	self.height = height
    	self.grid = [[0 for x in range (width)] for y in range(height)]

    def insert(self, x, y):
    	self.grid[x][y] = 1

    def remove(self, x, y):
    	self.grid[x][y] = 0

    def loc_taken(self, x, y):
    	return self.grid[x][y] == 1

    def draw(self):
    	for x in range(0, self.width):
    		for y in range(0, self.height):
    			sys.stdout.write('%s' % self.grid[x][y])
    		print()



class DragonArena:
    """The main game class"""
    def __init__(self, dragons, knights, worlds, map_width, map_height):
        self.no_of_dragons 	= dragons
        self.no_of_knights 	= knights
        self.no_of_worlds	= worlds
        self.map_width		= map_width
        self.map_height		= map_height

    def start(self):
    	# create worlds
    	worlds = [World(self.map_width, self.map_height) for i in range(self.no_of_worlds)]

    	creatures = []

    	# create Dragons in each world
    	for world in worlds:
    		for i in range(0, self.no_of_dragons):
    			while True:
    				rand_x = randint(0, self.map_width)
    				rand_y = randint(0, self.map_height)
    				if not world.loc_taken(rand_x, rand_y):
    					world.insert(rand_x, rand_y)
    					creatures.append(Dragon(rand_x, rand_y))
    					break

    	# create Knights in each world
    	for world in worlds:
    		for i in range(0, self.no_of_knights):
    			while True:
    				rand_x = randint(0, self.map_width-1)
    				rand_y = randint(0, self.map_height-1)
    				if not world.loc_taken(rand_x, rand_y):
    					world.insert(rand_x, rand_y)
    					creatures.append(Knight(rand_x, rand_y, self.map_width, self.map_height))
    					break

        # this can be done better, but had only terminal at the time so ye
    	for world in worlds:
    		world.draw()

    	#for creature in creatures:
    	#	if creature.get_name == "Dragon":
    	#		sys.stdout.write('%s' % '@')
    	#	elif creature.get_name == "Knight":
    	#		sys.stdout.write('%s' % '#')
    		
        
class Graphics:
    def show(self):
        # set up the colors
        BLACK = (0, 0, 0)
        WHITE = (255, 255, 255)
        RED = (255, 0, 0)
        GREEN = (0, 255, 0)
        BLUE = (0, 0, 255)

        # set up pygame
        pygame.init()

        # set up window
        window_surface = pygame.display.set_mode((600, 400), 0, 32)
        pygame.display.set_caption('Dragon Arena!')

        # set up fonts
        basic_font = pygame.font.SysFont(None, 32)

        # draw the background onto the surface
        window_surface.fill(WHITE)

        # draw a blue circle onto the surface
        pygame.draw.circle(window_surface, BLUE, (300, 50), 20, 0)

        
        # set up the text
        text = basic_font.render('Need to build grid display, but all components are here!', True, WHITE, BLUE)
        # draw the text onto the surface
        window_surface.blit(text, (10, 200))

        # draw the window onto the screen
        pygame.display.update()
        
        while True:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()


if __name__ == '__main__':
    #no_of_knights	= 100
    #no_of_dragons	= 20
    #no_of_worlds	= 3
    #map_width		= 25
    #map_height		= 25
    no_of_dragons = 1
    no_of_knights = 10
    no_of_worlds = 1
    map_width = 10
    map_height = 10


    # start DragonArena Controller
    game = DragonArena(no_of_dragons, no_of_knights, no_of_worlds, map_width, map_height)
    #game.start()
    graphics = Graphics()
    graphics.show()

