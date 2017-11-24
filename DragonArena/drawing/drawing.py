import os
import sys
import json
from sys import platform

sys.path.insert(1, os.path.join(sys.path[0], '../game-interface'))
from DragonArenaNew import Dragon, Knight

settings = json.load(open('../settings.json'))

# This is just used for drawing
DRAGON = settings["dragon"]["symbol"]  # Used to identify a dragon
PLAYER = settings["player"]["symbol"]  # Used to identify a knight/player
EMPTY = 0  # Used to identify an empty grid piece


class BoardVisualization:
    def __init__(self, game):
        self.game = game
        self.height = game.height
        self.width = game.width

        self.clear_screen()

    def draw_game(self):
        self.clear_screen()
        grid = self.game.get_sorted_grid_including_creatures()

        width = 0
        for x in grid:
            if isinstance(x, Dragon):
                print DRAGON,
            elif isinstance(x, Knight):
                print PLAYER,
            else:
                print EMPTY,

            width += 1
            if width == self.width+1:
                print "\n",
                width = 0

    def draw_game_for_world(self, index):
        self.clear_screen()
        self.game.draw_world(index)

    @staticmethod
    def clear_screen():
        if platform == "win32":
            os.system('cls')
        else:
            os.system('clear')
