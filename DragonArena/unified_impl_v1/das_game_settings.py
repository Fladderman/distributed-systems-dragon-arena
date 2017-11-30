backlog = 5
server_addresses = [
    # server with id==0 implicitly is connected to server_addresses[0]
    ("127.0.0.1", 2001),
    ("127.0.0.1", 2002),
    ("127.0.0.1", 2003),
    ("127.0.0.1", 2004),
    ("127.0.0.1", 2005),
]
num_server_addresses = len(server_addresses)

S2S_wait_for_welcome_timeout = 0.2
server_min_tick_time = 4.0

max_server_sync_wait = S2S_wait_for_welcome_timeout * (num_server_addresses + 1)
max_done_wait = server_min_tick_time + max_server_sync_wait + 1.0

dragon_arena_init_settings = {'no_of_dragons': 10,
                              'map_width': 25,
                              'map_height': 25
                              }

client_ping_max_time = 0.3
