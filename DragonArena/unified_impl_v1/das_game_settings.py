# INPUTS:
backlog = 5
server_addresses = [
    # server with id==0 implicitly is connected to server_addresses[0]
    ("127.0.0.1", 2001),
    ("127.0.0.1", 2002),
    ("127.0.0.1", 2003),
    ("127.0.0.1", 2004),
    ("127.0.0.1", 2005),
]
debug_printing = True
S2S_wait_for_welcome_timeout = 0.2
server_min_tick_time = 1.5
dragon_ap_bounds = [5, 20]
dragon_hp_bounds = [50, 100]
knight_ap_bounds = [2, 10]
knight_hp_bounds = [50, 100]
'''
# Here are the default values in case we change them:
dragon_ap_bounds = [5, 20]
dragon_hp_bounds = [50, 100]
knight_ap_bounds = [1, 10]
knight_hp_bounds = [10, 20]
'''

# A server will certainly not refuse a new client if the server
# has < min_server_client_capacity clients
min_server_client_capacity = 3

# A server will consider itself 'over capacity' if it has server
# overcapacity_ratio times the average server load
server_overcapacity_ratio = 4
dragon_arena_init_settings = {'no_of_dragons': 10,
                              'map_width': 25,
                              'map_height': 25
                              }
client_ping_max_time = 0.06
client_handshake_timeout = 0.5
dragon_attack_period = 1.0


# ############ DON'T TOUCH BELOW THIS LINE

def debug_print(*args):
    if debug_printing:
        print args

ticks_per_dragon_attack = int(round(dragon_attack_period/server_min_tick_time))
num_server_addresses = len(server_addresses)
max_server_sync_wait = S2S_wait_for_welcome_timeout * \
                       (num_server_addresses + 1)
max_done_wait = server_min_tick_time + max_server_sync_wait + 1.0
