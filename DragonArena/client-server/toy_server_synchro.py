import time
import base64
import threading

# Roy: a global note. We need to consider the fact that dragons perform
# actions as well, and that these actions need to be logged. My suggestion:
# we keep the total order on players events (Christopher already has one).
# After all player events are processed, dragon events are processed. Each
# server already has the same list of dragons. This order must be preserved
# throughout. From head to tail we then check: whether a dragon is alive, and
# if so, what its targets are. From these targets, the target is selected which
# has: (a) minimal health, and (b) a smallest (x,y) coordinate in the
# lexicographical ordering on coordinates. Note that (a) could be dropped if
# we want to keep things simple. However, we anyway need (b) to keep the target
# selection deterministic.
#
# Each dragon event is applied to the state and logged.


#pip install msgpack-python
import msgpack
DONE = 0

# set to 0.0 for no sleeping. Servers will wait ONLY for each other
TICK_TIME_MIN = 1.0
			

'''
# {sc, ss} : "this message is sent from server to client, AND from server to server"
# NAME	   : name of the message
# [a, b]   : message is sent with 2 comma separated args

{cs}		CLT_JOIN		[]
{ss}		SPAWN			[new_knight_ID, random_seed]
{sc}		CLT_WELCOME		[knight_ID, serialized_game_state, tick_ID]
{ss}		SRV_JOIN		[]
{ss}		SRV_WELCOME		[serialized_game_state, tick_ID]
{ss,cs}		DONE			[tick_ID]

{cs,ss}		R_ATTACK		[attacker_ID, attacked_ID, valid]
{cs,ss}		R_HEAL			[healer_ID, healed_ID, valid]
{sc,cs,ss}	RU_MOVE			[id, new_position, valid]
{ss,sc}		U_CREATE		[serialized_knight]
{sc}		U_HEALTH_IS		[id, new_health_value]
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
	'''
	def write_to(self, socket):
		naked_msg = (self.name, self.sender, self.args)
		msgpack.pack(naked_msg, socket)

	# Roy: why pack/unpack intead of packb/unpackb? Not a suggestive question,
	# it really is not clear to me from the docs which one you should use where.
	# (If we do use packb/unpackb, we would have to define naked_msg as a list.)

	
	'''
	CALLER IS RESPONSIBLE FOR SOCKET SYNCHRO!!
	call like this:		msg = Message.read_from(socket)
	reads from socket until it reads a complete message, deserializes it.
	'''
	def read_from(socket):
		naked_msg = msgpack.unpack(socket)
		assert len(naked_msg) == 3
		assert isinstance(naked_msg[2], list)
		return Message(naked_msg[0], naked_msg[1], naked_msg[2])
	
	# allows msg1==msg2 call. Returns true if identical message. Maybe unneeded?
	def __eq__(self, other):
		return self.name == other.name  and self.sender == other.sender  and self.args == other.args

	# Roy: eq is required
	#   https://docs.python.org/2/library/functools.html#functools.total_ordering
	# For performance we could also implement the other relations later.
	
	# 'is less than' function, relied upon for sort()
	# this function defines on the order requests get applied to the game state
	def __lt__(self, other):
		if a.name < b.name:                 return True  # Roy: changed elif to if
		elif a.name > b.name:               return False
		else: # a.name == b.name
			if len(a.args) < len(b.args):   return True
			elif len(a.args) > len(b.args): return False
			else: # len(a.args) == len(b.args)
				for (i,j) in a.args.zip(b.args):
					if str(i) < str(j):     return True 
					elif str(i) > str(j):   return False  # Roy: corrected < to >
		return False # equivalent!

server_lookup = { # hashmap from (ip,port) --> server_ID
	("127.0.0.1", 8000) : 0,
	("127.0.0.1", 8001) : 1,
	("127.0.0.1", 8002) : 2,
	("127.0.0.1", 8003) : 3,
	("127.0.0.1", 8004) : 4,
}
		
class Server:
	def __init__(self, server_id):
		self.server_id = server_id
		self.next_avail_client_ID = 100
		# this would assign 
		# Roy: your comment is incomplete here. "[..] ids to clients"?

		#locks
		self.req_buffer_lock = threading.Lock()
		self.state_lock = threading.Lock()
		
		# socket has .getpeername() which returns ip,port
		self.server_sockets = [];
		self.client_sockets = dict();  #client_ID --> socket
		self.waiting_client_sockets = [];

		# Roy: what is waiting_client_sockets for?
		
		'''
		conceptually this is a multi-set
		implementation options:
			set : 		fast {element check}
			multiset :	fast-ish {element check}, duplicates
			list : 		fast {iteration, append}
		>> LIST best suits our needs
		'''
		# Roy: where do these figures come from? Should checking membership
		# for a multiset not be just as fast as for a set?
		# Either way, we will indeed not check for membership (I think) and
		# insertion can be O(1) rather than O(log n). So list seems
		# best to me as well.

		self.req_buffer = []

		# Roy: we have all kinds of maps. E.g. from (ip,port) to id,
		# id to socket, for both clients and servers. How about some naming
		# conventions? client_addr2id, client_addr2socket, server_id2addr, etc.
		#  So: <type>_<from>2<to>
		# with type in {client, server}, and from,to in {addr,socket,id}.
		# That covers at least all 12 existing cases, maybe more properties
		# arrive later?
		#   Also, I was wondering: can we not hardcore which port a client will
		# listen to? Then the association between clients and ports is not 
		# necessary.
		
		# maps (ip,port) --> client_ID
		self.client_lookup = dict()
		
		''' TODO here. try connect to others. do the whole connecting jazz'''
		
	def _apply_request(game_state, req):
		'''
		TODO
		either:
			make NO change to game_state. return None
			change game_state. Return appropriate UPDATE to reflect the change
		'''
		pass
		
	def _handle_serv_join(self, socket):
		with self.state_lock:
			#TODO
			msg = Message('''TODO''')
			msg.write_to(socket)
	
	# collects incoming messages. doesn't return until DONE signal
	def _accept_messages_until_done(socket, current_tick_id):
		s = []
		while True:
			msg = Message.read_from(socket)
			if msg.name == 'DONE': return s
			else: s.append(msg)

	def server_tick_loop(self, start_tick_id):
		# first server has start_tick_id == 0. others >= 0 
		tick_id = start_tick_id
		while True:					
			tick_start = time.time() # get START TIME
			
			#swap out req_buffer (lock because messages are still cominig in)
			with req_buffer_lock:
				tick_req_multiset = self.req_buffer
				self.req_buffer = []
				
			#tick_req_multiset currently is only my local reqs. flood to others
			
			done_msg = Message("DONE", self.server_ID, [tick_ID])
			for socket in self.server_sockets:
				for req in my_reqs:
					req.write_to(socket)
				done_msg.write_to(socket)
			del my_reqs
					
			# This loop acts as the barrier
			for socket in self.server_sockets:
				# collect reqs. returns when receives DONE
				tick_req_multiset.extend(_accept_messages_until_done(socket))
				
			outgoing_updates = []
			tick_req_multiset.sort() # in-place list sort, relying on Message.__lt__() for ordering
			player_has_acted = {}
			with open(LOG_PATH, "a") as log_file: # "a" for append mode
				with self.state_lock: #assures cant ever read a state while its being modified
					for req in tick_req_multiset:
						log_file.write(str(tick_id) + "\t" + str(req))
						# _apply_req_return_success() either:
							
						if req.name == "SPAWN":
							update = self._apply_request(req)
							if update != None:
								if req.sender == self.server_ID:
									cid = self.next_avail_client_ID;
									sock = waiting_client_sockets.pop(0) #TODO panics if client has left
									assert cid not in self.client_sockets	# should never be a problem
									self.client_sockets.insert(cid, sock)
								self.next_avail_client_ID += 1;
								
						if req.sender not in player_has_acted:
							player_has_acted.add(req.sender)
							update = self._apply_request(req)
							if update != None:
								outgoing_updates.append(req)
				log_file.flush()
			outgoing_updates = agglutinate_updates(outgoing_updates)
					
			# flood. no synchro needed. only this thread writes out.
			done_msg = Message("DONE", self.server_ID, [tick_ID])
			for socket in self.client_sockets.values():
				for u in outgoing_updates:
					u.write_to(socket)
				socket.write_to(socket)
					
			sleep(max(0.0, time.time() - tick_start + TICK_TIME_MIN))
			# at least ~TICK_TIME_MIN has passed since 'tick_start' was defined
					
			tick_id += 1
			# tick done. loop again