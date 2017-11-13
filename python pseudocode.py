
# server_list = [addr0, addr1, ... addr4]

RequestType = Enum('MOVE', 'ATTACK', 'HEAL') # client tells server its knight's intentions
UpdateType = Enum('MOVE', 'ADD', 'REMOVE', 'HEALTH_CHANGE') # server just tells client what happens.
EntityType = Enum('DRAGON', 'KNIGHT')

class GameState:
	# class that both client and server have. represent the game state

	def __init__(self):
		knights = dict() # stores tuple pairs of (x,y) coordinates
		dragons = dict()
		
	def render(self, gui):
		`draw_background`()
		for (eid, k) in self.knights:
			`draw_knight_at`(k[0], k[1])
		for (eid, k) in self.dragons:
			`draw_dragon_at`(d[0], d[1])
		
	def add_entity(self, eid : int, e_type : EntityType, x, y):
		self.entities[eid] = (e_type, x, y)
		
	def remove_entity(self, eid : int):
		self.entities.remove(eid)
		
	def move_entity(self, eid : int, x, y)
		e = self.entities[eid]
		self.entities[eid] = (e[0], x, y)


def server(server_list, my_id):
	'''TODO'''
	pass
	

'''
The client main loop
'''
def client(server_list):

	# client helper functions

	def setup_state(socket):
		state = GameState()
		x = send(socket, ['NEW_PLAYER'])
		(player_id, initial_state, tick_id) = x.receive('WELCOME')

	def input_request_loop(locked_state, socket, gui):
		gui.event_blocking = True
		while True:
			event = gui.get_next_event()
			'''
			lots of complex nested if-else clusters
			to create requests, much like the update_loop.
			'''

	def update_loop(locked_state, socket, tick_id, server_list, player_id):
		while True:
			msg = socket.read()
			if msg == CRASH:
				'''
				move head of server_list to back. connect to new head server
				get all missed state updates by telling server 'tick_id'
				'''
			else:
				with s = locked_state.lock() 
					parsed_msg = parse_update(msg)
					`apply_update`(locked_state, parsed_msg)
					# implicit s unlock
						
					

	def render_loop(locked_state, gui):
		while True:
			thread.sleep(1000/30) # 30 fps
			with s = locked_state.lock()
				gui.clear_screen()
				s.render(gui)
				# implicit s unlock
				
				
	seed = time_now()
	rand = rand_by_seed(seed)
	server_list.shuffle_by_random_generator(rand) # ensure each client has a random ordering of servers
	
	socket = tcp_connect(server_list[0]) # each client contacts a different server
	socket.timeout = None # socket.read() will block until it returns or crashes. under the hood its constantly polling
	
	(player_id, initial_state, tick_id) = setup_state(server_list[0])
	locked_state = Mutex(socket)
	
	gui = Gui()
	
	thread.start_new_thread(input_request_loop, [locked_state, socket, gui]) #spawn thread to enter request loop
	thread.start_new_thread(update_loop, [locked_state, socket, server_list, player_id]) #spawn thread to enter update loop
	render_loop(locked_state, gui) # main thread enters render loop
		
	