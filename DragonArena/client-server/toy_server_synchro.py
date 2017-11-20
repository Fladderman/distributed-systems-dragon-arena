import time
import base64
import threading

DONE = 0
TICK_TIME_MIN = 1.0


def compare_msgs(a, b):
	if a.name < b.name:                 return -1
	elif a.name > b.name:               return 1
	else:
		if len(a.args) < len(b.args):   return -1
		elif len(a.args) > len(b.args): return 1
		else:
			for (i,j) in a.args.zip(b.args):
				if str(i) < str(j):     return -1
				elif str(i) < str(j):   return 1
	return 0

class Message:
	def __init__(self, name, args):
		self.name = name # some idenfier. must support == 
		self.args = args # list of args. [] if none
		
	def serialize(self):
		str = base64.encode(self)
		for (i, val) in self.args.enumerate():
			
		# return a byte array adhering to :,! format
		
	def deserialize(bytes):
		pass
		# note: invoke with:	msg = Message.deserialize(bytes)
		# returns instance of Message                      return 0
	
class Server:
	def __init__(self):
		self.req_buffer_lock = threading.Lock()
		
	def atomic_req_buffer_add(self, msg):
		self.req_buffer_lock.acquire()
		self.req_buffer.append(msg)
		self.req_buffer_lock.release()
		
	def atomic_drain_req_buffer(self):
		self.req_buffer_lock.acquire()
		x = self.req_buffer
		self.req_buffer = []
		self.req_buffer_lock.release()
		return x

	def server_loop(self):
		tick_id = 0
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
			
			# returns a LIST (conceptually a set, but we can save time spent for dedup)
			# need synchro. 1 thread listening per client
			my_reqs = self.atomic_drain_req_buffer()
			
			total_reqs = my_reqs[:]
			for req in my_reqs:
				for socket in self.other_servers:
					socket.send_msg(req)
					
			# This loop acts as the barrier
			for socket in self.other_servers:
				# collect reqs. returns when receives DONE
				total_reqs.extend(accept_messages_until_ack(socket))
				
			outgoing_updates = []
			total_reqs.sort(key = compare_msgs) # in-place list sort, relying on compare_msgs() for ordering
			with open(LOG_PATH, "a") as log_file: # "a" for append mode
				for req in total_reqs:
					log_file.write(req) # implicit stringify call of req.__repr__()
					'''PSEUDO
					if game_state.valid_action(req)
					outgoing_updates.append()
					'''
					
			# flood. no synchro needed. only this thread writes out.
			for socket in self.other_servers:
				for u in outgoing_updates:
					socket.write(u)
					
			tick_id += 1
			
	def 

	