import os
from sys import platform


class BoardVisualization:
    def __init__(self, game):
        self.game = game

        self.clear_screen()

    def draw_game(self):
        self.clear_screen()
        self.game.draw_worlds()

    def draw_game_for_world(self, index):
        self.clear_screen()
        self.game.draw_world(index)

    @staticmethod
    def clear_screen():
        if platform == "win32":
            os.system('cls')
        else:
            os.system('clear')
