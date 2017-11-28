backlog = 5
server_addresses = [
#server with id==0 implicity is connected to server_addresses[0]
    ("127.0.0.1", 2001),
    ("127.0.0.1", 2002),
    ("127.0.0.1", 2003),
    ("127.0.0.1", 2004),
    ("127.0.0.1", 2005),
]
num_server_addresses = len(server_addresses)
server_min_tick_time = 4.0
dragon_arena_init_settings = {'no_of_dragons':10, 'map_width':25, 'map_height':25}
