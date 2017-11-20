import time
import base64
import threading
import cPickle as pickle

DONE = 0
TICK_TIME_MIN = 1.0
			

'''
# {sc, ss} : "this message is sent from server to client, AND from server to server" 	
# NAME	   : name of the message
# [a, b]   : message is sent with 2 comma separated args

{cs}		CLT_JOIN	[]
{sc}		CLT_WELCOME	[knight_ID, serialized_game_state, tick_ID]
{ss}		SRV_JOIN	[]
{ss}		SRV_WELCOME	[serialized_game_state, tick_ID]

{cs,ss}		R_ATTACK	[attacker_ID, attacked_ID]
{cs,ss}		R_HEAL		[healer_ID, healed_ID]
{sc,cs,ss}	RU_MOVE		[id, new_position]
{ss,cs,sc}	RU_CREATE	[serialized_knight]
{sc}		U_HEALTH_IS	[id, new_health_value]
'''
		
def agglutinate_updates(update_list):
	'''
	TODO
	eg ((x attack y + z attack y + a heal y) --> (y health_change q))
	leave this function AS-IS for no deduplication. will still work correctly.
	'''
	return update_list
			
			
class Message:
	def __init__(self, name, sender, args):
		self.name = name # some idenfier. must support == 
		self.sender = sender
		self.args = args # list of args. [] if none
	
	'''
	CALLER IS RESPONSIBLE FOR SOCKET SYNCHRO!!
	call like this:		msg.write_to(socket)
	serializes this message and writes it to socket
	adds escape and end-delim chars
	'''
	def write_to(self, socket):
		raw = pickle.dumps(self, f, pickle.HIGHEST_PROTOCOL)
		# using '?' as escape character. this allows the reader to not need a look-ahead
		ready = raw.replace('?', '??').replace('!', '?!')
		socket.write(ready + '!')
	
	'''
	CALLER IS RESPONSIBLE FOR SOCKET SYNCHRO!!
	call like this:		msg = Message.read_from(socket)
	reads from socket until it reads a complete message, deserializes it.
	Return type is Message
	expects to read escape and end-delim chars
	'''
	def read_from(socket):
		s = ''
		escaped = False
		while True:
			c = socket.read(1)
			if len(s) > 100:
				#client messages are pretty short. it's misbehaving
				print('WTF, where is the end? this is a long ass message')
				# TODO shutdown socket and continue on.
				exit(1)
			if escaped or (c != '?' and c != '!'):
				escaped = False #consume escape
				s += x
			elif c == '?':
				escaped = True
			else c == '!':
				# this '!' must be the end delim
				break;	#stop reading. omit '!', 
		msg = pickle.loads(s)
		return msg
	
	# allows msg1==msg2 call. Returns true if identical message. Maybe unneeded?
	def __eq__(self, other):
		return self.name == other.name \
		and self.sender == other.sender \
		and self.args == other.args
	
	# 'is less than' function, relied upon for sort()
	# this function defines on the order requests get applied to the game state
	def __lt__(self, other):
		# TODO give RU_CREATE the highest priority to give spawning in the best chance of success
		if a.name < b.name:                 return True
		elif a.name > b.name:               return False
		else:
			if len(a.args) < len(b.args):   return True
			elif len(a.args) > len(b.args): return False
			else:
				for (i,j) in a.args.zip(b.args):
					if str(i) < str(j):     return True
					elif str(i) < str(j):   return False
		return False # equivalent!

server_lookup = { # hashmap from (ip,port) --> server_ID
	("127.0.0.1", 8000) : 0,
	("127.0.0.1", 8001) : 0,
	("127.0.0.1", 8002) : 0,
	("127.0.0.1", 8003) : 0,
	("127.0.0.1", 8004) : 0,
}
		
class Server:
	def __init__(self, server_id):
		self.req_buffer_lock = threading.Lock()
		self.state_lock = threading.Lock()
		self.server_sockets = [];
		self.client_sockets = [];
		self.clients_waiting_for_spawn = [];
		self.client_lookup = dict()
		
		# TODO try connect to others. do the whole connecting jazz
		
	def atomic_req_buffer_add(self, msg):
		self.req_buffer_lock.acquire()
		self.req_buffer.append(msg)
		self.req_buffer_lock.release()
		
	def atomic_drain_req_buffer(self):
		with req_buffer_lock:
			x = self.req_buffer
			self.req_buffer = []
		return x
		
	def apply_req_return_success(game_state, req):
		'''
		TODO game code goes here. 
		IF successful, return True
		OTHERWISE return False
		'''
		pass
		
	def got_serv_join(self, socket):
		with self.state_lock:
			msg = Message('SRV_WELCOME', '')
		

	def server_tick_loop(self, start_tick_id):
		# first server has start_tick_id == 0. others >= 0 
		tick_id = start_tick_id
		while True:
			#define a local helper function
			def accept_messages_until_done(socket):
				s = []
				while True:
					msg = Message.deserialize(socket.recv_msg())
					if msg.name == DONE:
						return s
					s.append(msg)
					
			tick_start = time.time() # get START TIME
			
			'''
			this is the SET of total updates.
			Implmented as a LIST because sets will remove duplicate requests
				(which we need to retain for logging)
			need synchro. 1 thread listening per client
			'''
			with req_buffer_lock:
				my_reqs = self.req_buffer
				self.req_buffer = []
			
			total_reqs = my_reqs[:]
			for req in my_reqs:
				for socket in self.server_sockets:
					socket.send_msg(req)
					
			# This loop acts as the barrier
			for socket in self.server_sockets:
				# collect reqs. returns when receives DONE
				total_reqs.extend(accept_messages_until_ack(socket))
				
			outgoing_updates = []
			total_reqs.sort() # in-place list sort, relying on Message.__lt__() for ordering
			player_has_acted = {}
			with open(LOG_PATH, "a") as log_file: # "a" for append mode
				with self.state_lock: #assures cant ever read a state while its being modified
					for req in total_reqs:
						if req.sender not in player_has_acted:
							player_has_acted.add(req.sender)
							log_file.write(str(tick_id) + "\t" str(req))
							
							# apply_req_return_success() changes game state. 
							if self.apply_req_return_success(req):
								outgoing_updates.append(req)
			
			outgoing_updates = agglutinate_updates(outgoing_updates)
					
			# flood. no synchro needed. only this thread writes out.
			for socket in self.server_sockets:
				for u in outgoing_updates:
					socket.write(u)
					
			sleep(max(0.0, time.time() - tick_start + TICK_TIME_MIN))
			# at least ~TICK_TIME_MIN has passed since 'tick_start' was defined
					
			tick_id += 1
			# tick done. loop again