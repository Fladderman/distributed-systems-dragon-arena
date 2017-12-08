import logging
# from __future__ import print_function
'''
Levels:
CRITICAL
ERROR
WARNING
INFO
DEBUG
NOTSET
'''

# INPUTS:
backlog = 5
server_addresses = [
    # server with id==0 implicitly is connected to server_addresses[0]
    ("10.141.0.120", 2001),
    ("10.141.0.121", 2002),
    ("10.141.0.122", 2003),
    ("10.141.0.123", 2004),
    ("10.141.0.124", 2005),
]

# #DEBUG. overwriting
# server_addresses = [
#     ("127.0.0.1", 2001),
#     ("127.0.0.1", 2002),
#     ("127.0.0.1", 2003),
#     ("127.0.0.1", 2004),
#     ("127.0.0.1", 2005),
# ]
debug_printing = False
server_visualizer = False
client_visualizer = True
suppress_game_over = False
S2S_wait_for_welcome_timeout = 0.2
server_min_tick_time = 0.2
ticks_per_game_hash = 4
server_secret_salt = 'e4f421af'

# change to logging.CRITICAL if you only want DAS/Player game event logs
logging_level = logging.DEBUG

dragon_ap_bounds = [1, 2]
dragon_hp_bounds = [30, 50]
knight_ap_bounds = [1, 1]
knight_hp_bounds = [280, 300]
'''
# Here are the default values in case we change them:
dragon_ap_bounds = [5, 20]
dragon_hp_bounds = [50, 100]
knight_ap_bounds = [1, 10]
knight_hp_bounds = [10, 20]
'''

# A server will certainly not refuse a new client if the server
# has < min_server_client_capacity clients
min_server_client_capacity = 5

# A server will consider itself 'over capacity' if it has server
# overcapacity_ratio times the average server load
# while overcapacity, a server will refuse NEW connections
server_overcapacity_ratio = 1.2

# while very overcapacity, a server will PRUNE existing connections
server_very_overcapacity_ratio = 1.3

dragon_arena_init_settings = {'no_of_dragons': 10,
                              'map_width': 25,
                              'map_height': 25
                              }
client_ping_max_time = 0.09

# average ticks per attack
dragon_attack_period = 2.0


# ############ DON'T TOUCH BELOW THIS LINE
assert server_overcapacity_ratio > 1.0
assert server_very_overcapacity_ratio > server_overcapacity_ratio

def debug_print(*args):
    if debug_printing:
        print(args)

ticks_per_dragon_attack = \
    max(1, int(round(dragon_attack_period / server_min_tick_time)))
num_server_addresses = len(server_addresses)
max_server_sync_wait = S2S_wait_for_welcome_timeout * \
                       (num_server_addresses + 1)

client_handshake_timeout = server_min_tick_time * 1.3 + 0.2
max_done_wait = server_min_tick_time + max_server_sync_wait + 1.0
