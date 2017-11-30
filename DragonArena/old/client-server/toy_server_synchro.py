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
# NAME       : name of the message
# [a, b]   : message is sent with 2 comma separated args

{cs}        CLT_JOIN        []
{ss}        SPAWN           [new_knight_ID, random_seed]
{sc}        CLT_WELCOME     [knight_ID, serialized_game_state, tick_ID]
{ss}        SRV_JOIN        []
{ss}        SRV_WELCOME     [serialized_game_state, tick_ID]
{ss,cs}     DONE            [tick_ID]

{cs,ss}     R_ATTACK        [attacker_ID, attacked_ID, valid]
{cs,ss}     R_HEAL          [healer_ID, healed_ID, valid]
{sc,cs,ss}  RU_MOVE         [id, new_position, valid]
{ss,sc}     U_CREATE        [serialized_knight]
{sc}        U_HEALTH_IS     [id, new_health_value]
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
    call like this:        msg.write_to(socket)
    '''
    def write_to(self, socket):
        naked_msg = (self.name, self.sender, self.args)
        msgpack.pack(naked_msg, socket)

    # Roy: why pack/unpack intead of packb/unpackb? Not a suggestive question,
    # it really is not clear to me from the docs which one you should use where.
    # (If we do use packb/unpackb, we would have to define naked_msg as a list.)


    '''
    CALLER IS RESPONSIBLE FOR SOCKET SYNCHRO!!
    call like this:        msg = Message.read_from(socket)
    reads from socket until it reads a complete message, deserializes it.
    '''
    def read_from(socket):
        naked_msg = msgpack.unpack(socket)
        assert len(naked_msg) == 3
        assert isinstance(naked_msg[2], list)
        return Message(naked_msg[0], naked_msg[1], naked_msg[2])

    # allows msg1==msg2 call. Returns true if identical message.
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
		self.game_state = _get_game_state() #TODO
        # this would assign
        # Roy: your comment is incomplete here. "[..] ids to clients"?

        #locks
        '''
        TODO
        http://effbot.org/pyfaq/what-kinds-of-global-value-mutation-are-thread-safe.htm
        some things in python are thread-safe. It may be possible to (for example) not need a lock for req_buffer
        .pop() is thread-safe, and throws exception if empty. so try,pop,except
        should be safe and can be used a s drain() operation
        '''
        self.req_buffer_lock = threading.Lock()
        self.state_lock = threading.Lock()

        # socket has .getpeername() which returns ip,port
        self.server_sockets = [];
        self.client_sockets = dict();  #client_ID --> socket
        self.waiting_client_sockets = [];
        self.waiting_server_sockets = []; #<== server has contacted this clie

        # Roy: what is waiting_client_sockets for?

        '''
        conceptually this is a multi-set
        implementation options:
            set :         fast {element check}
            multiset :    fast {element check}, fast-ish {duplicates}
            list :        fast {iteration, append}
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


	def _apply_request_sequence(self, req_sequence, tick_id):
		outgoing_updates = []
		player_has_acted = {}
		with open(LOG_PATH, "a") as log_file: # "a" for append mode
			with self.state_lock: #assures cant ever read a state while its being modified
				for req in req_sequence:
					log_file.write(str(tick_id) + "\t" + str(req))  # log every request
					#TODO check this part for correctness
					if req.name == "SPAWN":
						update = self._apply_request(req)
						if update != None:
							if req.sender == self.server_ID:
								cid = self.next_avail_client_ID;
								sock = waiting_client_sockets.pop(0) #TODO panics if client has left
								assert cid not in self.client_sockets    # should never be a problem
								self.client_sockets.insert(cid, sock)
							# all servers incriment next_avail_ID
							self.next_avail_client_ID += 1;

					if req.sender not in player_has_acted:  # one request per client per tick
						player_has_acted.add(req.sender)
						update = self._apply_request(req)
						if update != None:  # only produce (and store) updates for requests that mutate state
							outgoing_updates.append(req)
			log_file.flush()

		# optimization. attempt to represent the same update sequence more succinctly
		outgoing_updates = agglutinate_updates(outgoing_updates)
		return outgoing_updates

	'''warning ! deadlock condition if two servers call this in the same tick!!!'''
	def _servers_join_server_tick(self, my_request_multiset, tick_id):

		'''STEP `send_batch`: send out buffered requests. DO NOT send out DONEs'''
		for socket in self.server_sockets:
			for req in my_request_multiset:
				req.write_to(socket)

		'''STEP `recv&wait`: receive requests. wait for DONEs (acts as barrier!)'''
		all_requests = my_request_multiset
		for socket in self.server_sockets:
			# collect reqs. returns when receives DONE
			all_requests.extend(_accept_messages_until_done(socket))

		#################################### ONLY THIS SERVER LEAVES BARRIER, others wait #################################

		'''STEP `sort_reqs`: order the requests. every server now has the same list'''
		tick_req_sequence = all_requests.sorted() # in-place list sort, relying on Message.__lt__() for ordering

		'''STEP `apply_reqs`: iterate over ordered requests. log each one. attempt to mutate game state. produce update when successful'''
		outgoing_updates = self._apply_request_sequence(tick_req_sequence, tick_id)

		'''SPECIAL STEP `sync_newcomer`: send the new server the newest game state'''
		while True:
			try:
				new_serv_socket = self.waiting_server_sockets.pop()
				state_update_message = Message("SRV_WELCOME", self.server_ID, [self.game_state, tick_ID])
				state_update_message.write_to(new_serv_socket)
				self._accept_messages_until_done(new_serv_socket) '''wait for that server to ack with DONE'''
				# new_serv_socket is ALREADY in server_sockets list
			except:
				break # no more waiting in the list

		'''STEP `send_done`: send out DONEs, releasing the barrier'''
		done_msg = Message("DONE", self.server_ID, [tick_ID])
		for socket in self.server_sockets:
			for req in my_request_multiset:
				req.write_to(socket)
			done_msg.write_to(socket

		#################################### ALL `OTHER` SERVERS LEAVE BARRIER #################################

		'''STEP `send_updates`: flood update sequence to each client'''
		# no synchro needed. only this thread writes out.
		done_msg = Message("DONE", self.server_ID, [tick_ID])
		for socket in self.client_sockets.values():
			for u in outgoing_updates:
				u.write_to(socket)
			socket.write_to(socket)

	def _normal_server_tick(self, my_request_multiset, tick_id):

		'''STEP `send_batch`: send out buffered requests. send out DONEs'''
		'''STEP `send_done`: send out buffered requests. send out DONEs'''
		done_msg = Message("DONE", self.server_ID, [tick_ID])
		for socket in self.server_sockets:
			for req in my_request_multiset:
				req.write_to(socket)
			done_msg.write_to(socket)

		'''STEP `recv&wait`: receive requests. wait for DONEs (acts as barrier!)'''
		all_requests = my_request_multiset
		for socket in self.server_sockets:
			# collect reqs. returns when receives DONE
			all_requests.extend(_accept_messages_until_done(socket))

		#################################### ALL SERVERS LEAVE BARRIER #################################


		'''STEP `sort_reqs`: order the requests. every server now has the same list'''
		tick_req_sequence = all_requests.sorted() # in-place list sort, relying on Message.__lt__() for ordering

		'''STEP `apply_reqs`: iterate over ordered requests. log each one. attempt to mutate game state. produce update when successful'''
		outgoing_updates = self._apply_request_sequence(tick_req_sequence, tick_id)

		'''STEP `send_updates`: flood update sequence to each client'''
		# no synchro needed. only this thread writes out.
		done_msg = Message("DONE", self.server_ID, [tick_ID])
		for socket in self.client_sockets.values():
			for u in outgoing_updates:
				u.write_to(socket)
			socket.write_to(socket)

    def server_tick_loop(self, start_tick_id):
        # first server has start_tick_id == 0. others >= 0
        tick_id = start_tick_id
        while True:
            tick_start = time.time() # get START TIME. required to enforce lower bound on tick time

			'''STEP `swap_batch`: swap buffers'''
			with req_buffer_lock:
				my_request_multiset = self.req_buffer
				self.req_buffer = []

			if len(self.waiting_server_sockets) == 0:
				'''!!! NORMAL SERVER TICK, step order:
				[send_batch, send_done, recv&wait, sort_reqs, apply_reqs, ______, _______, send_updates]
				'''
	            self._normal_server_tick(my_request_multiset, tick_id)
			else:
				'''!!! SERVER(S)-JOINING SERVER TICK, step order
				[send_batch, ______, recv&wait, sort_reqs, apply_reqs, sync_newcomer(s), send_done, send_updates]
				'''
	            self._normal_server_tick(my_request_multiset, tick_id)

            '''STEP `sleep`: sleep until tick time over'''
            sleep(max(0.0, time.time() - tick_start + TICK_TIME_MIN))
            # at least ~TICK_TIME_MIN has passed since 'tick_start' was defined

            tick_id += 1
            # tick done. loop again
