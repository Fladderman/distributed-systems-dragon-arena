import msgpack
import socket
import logging
from StringIO import StringIO
from das_game_settings import debug_print

"""
messages are stored and sent using integers in the header field
this is for compactness. For readability, the following two
structures allow mapping back and forth:
    int2header[<int>] ==> <str>
    header2int[<str>] ==> <int>
"""
int2header = [
    'S2S_SYNC_REQ',
    'S2S_SYNC_REPLY',
    'S2S_HELLO',
    'S2S_WELCOME',
    'S2S_SYNC_DONE',
    'PING',
    'C2S_HELLO',
    'C2S_HELLO_AGAIN',
    'S2C_WELCOME',
    'REFUSE',
    'SPAWN',
    'DESPAWN',
    'DONE',
    'DONE_HASHED',
    'UPDATE',
    'S2S_UPDATE',
    'R_HEAL',
    'R_ATTACK',
    'R_MOVE',
]
header2int = {v: k for k, v in enumerate(int2header)}


def listify(x):
    if isinstance(x, tuple) or isinstance(x, list):
        return [listify(y) for y in x]
    else:
        return x

def is_message_with_header_string(msg, header_string):
    if isinstance(msg, Message):
        return header2int[header_string] == msg.msg_header
    elif msg == MessageError.CRASH or msg == MessageError.TIMEOUT:
        return False
    else:
        raise ValueError(("Neither Message nor MessageError "
                          "instance was given: {}").format(str(msg)))


class Message:
    """
    Each Message instance represents an instance of any network message
    """

    def __init__(self, msg_header, sender, args):
        # print('init', msg_header, sender, args)
        try:
            assert isinstance(msg_header, int) and \
                   msg_header in range(0, len(int2header))
            assert isinstance(sender, int) or isinstance(sender, list) or isinstance(sender, tuple)
            assert isinstance(args, list)
            self.msg_header = msg_header
            if isinstance(sender, int):
                self.sender = sender
            else:
                self.sender = tuple(sender)
            self.args = args
            # print('WENT OK', self.msg_header, self.sender, self.args)
        except Exception as e:
            print('MESSAGE INIT FAILED!', msg_header, sender, args)
            # print('went bad!')
            debug_print('MESSAGE INIT FAILED', msg_header, sender, args)
            raise e

    def permitted_by_clients(self):
        return int2header[self.msg_header] in {'MOVE', 'ATTACK', 'HEAL'}

    def permitted_in_server_application_function(self):
        return (self.permitted_by_clients
                or self.msg_header == header2int['SPAWN']
                or self.msg_header == header2int['DESPAWN'])

    def header_matches_string(self, string):
        try:
            assert string in header2int
            return header2int[string] == self.msg_header
        except Exception as e:
            debug_print('header_matches_string FAILED')
            raise RuntimeError(e)

    def same_header_as(self, other):
        if other is None:
            return False
        assert isinstance(other, Message)
        return self.msg_header == other.msg_header

    def __eq__(self, other):
        if isinstance(other, Message):
            return self.msg_header == other.msg_header \
                and listify(self.sender) == listify(other.sender) \
                and listify(self.args) == listify(other.args)
        else:
            return False

    # We just want a deterministic and total order on msgs that is hardware
    # independent. It relies on the following:
    # - comparison between tuples is lexicographic
    # - msg_header is an integer
    # - sender is a tuple or an int. < between ints and tuples is supported
    # - args is a list of whatever, NOT containing objects that stringify
    #   to memory locations. so str will have the same outcome wherever it is
    #   called, and < is lexicographical for strings
    def __lt__(self, other):
        return (self.msg_header, listify(self.sender), str(listify(self.args))) < \
               (other.msg_header, listify(other.sender), str(listify(other.args)))

    def serialize(self):
        return self.msg_header, self.sender, self.args

    @staticmethod
    def deserialize(serialized_msg):
        try:
            msg_header = serialized_msg[0]
            sender = serialized_msg[1]
            args = serialized_msg[2]
            return Message(msg_header, sender, args)
        except Exception as e:
            logging.info("failed to deserialize {serialized_msg}".format(
                serialized_msg=serialized_msg))
            print ('Msg DESERIALIZE FAILED, INPUT: <', serialized_msg, e)
            raise e

    def __repr__(self):
        try:
            assert 0 <= self.msg_header < len(int2header)
            return 'Message::' + int2header[self.msg_header] + ' from ' \
                + str(self.sender) + ' with args:' + str(self.args)
        except Exception as e:
            debug_print('Msg REPR FAILED')
            raise RuntimeError(e)


"""
Predefined messages
# TODO check the protocol
maybe simplify? idk
"""

# TODO make more graceful
# TODO fill in some sender fields. (BEWARE! calling
# incomplete functions crashes silently)

# SERVER-SERVER SYNCHRONIZATION


def M_S2S_SYNC_REQ(s_id, hashed_serv_secret):
    return Message(header2int['S2S_SYNC_REQ'], s_id, [hashed_serv_secret])


def M_S2S_SYNC_REPLY(tick_id, serialized_state):
    return Message(header2int['S2S_SYNC_REPLY'], -1,
                   [tick_id, serialized_state])


def M_S2S_HELLO(s_id, hashed_serv_secret):
    return Message(header2int['S2S_HELLO'], s_id, [hashed_serv_secret])


def M_S2S_WELCOME(s_id):
    return Message(header2int['S2S_WELCOME'], s_id, [])


def M_REFUSE():
    return Message(header2int['REFUSE'], -1, [])


def M_S2S_SYNC_DONE():
    return Message(header2int['S2S_SYNC_DONE'], -1, [])

def M_DONE_HASHED(s_id, tick_id, num_clients, state_hash, servers_up):
    return Message(header2int['DONE_HASHED'], s_id, [tick_id, num_clients, state_hash, servers_up])

def M_DONE(s_id, tick_id, num_clients):
    return Message(header2int['DONE'], s_id, [tick_id, num_clients])

# SERVER-CLIENT SYNCHRONIZATION


def M_PING():
    # just nonsense for now. works as long as they are unique
    return Message(header2int['PING'], -1, [])


def M_C2S_HELLO(salt):
    return Message(header2int['C2S_HELLO'], -1, [salt])


def M_C2S_HELLO_AGAIN(salt, knight_id, secret):
    return Message(header2int['C2S_HELLO_AGAIN'], -1,
                   [salt, knight_id, secret])


def M_S2C_WELCOME(s_id, knight_id, secret):
    return Message(header2int['S2C_WELCOME'], s_id, [knight_id, secret])


def M_UPDATE(s_id, tick_id, serialized_state):
    return Message(header2int['UPDATE'], s_id, [tick_id, serialized_state])


def M_S2S_UPDATE(s_id, tick_id, serialized_state, previous_hash):
    return Message(header2int['S2S_UPDATE'], s_id, [tick_id, serialized_state,
                                                    previous_hash])


def M_SPAWN(s_id, knight_id):
    return Message(header2int['SPAWN'], s_id, [knight_id])


def M_DESPAWN(s_id, knight_id):
    return Message(header2int['DESPAWN'], -1, [knight_id])

# GAME REQUIREMENTS


def M_R_HEAL(healed):
    return Message(header2int['R_HEAL'], -1, [healed])


def M_R_ATTACK(attacked):
    return Message(header2int['R_ATTACK'], -1, [attacked])


def M_R_MOVE(direction):
    # direction is a char 'u', 'l', 'r', 'd'
    return Message(header2int['R_MOVE'], -1, [direction])


class MessageError:
    CRASH = 1
    TIMEOUT = 2


def read_msg_from(sock, timeout=None):
    assert timeout is None or isinstance(timeout, float)
    '''
    attempts to read exactly ONE message from the given socket
    may return Message
    may return MessageError.CRASH
    if timeout is not None:
        may return MessageError.TIMEOUT
    '''
    unpacker = msgpack.Unpacker()
    while True:
        try:
            sock.settimeout(timeout)
            x = sock.recv(1)
            if x == '':
                debug_print('socket dead!')
                return MessageError.CRASH
                # connection closed
            unpacker.feed(x)
            for package in unpacker:
                x = Message.deserialize(package)
                debug_print('     ::read msg', x)
                return x
        except socket.timeout:
            debug_print("timeout error")
            return MessageError.TIMEOUT
        except Exception as e:
            debug_print("sth else occurred: ", e)
            return MessageError.CRASH


def generate_messages_from(sock, timeout=True):
    debug_print('ITSYABOI, GENERATOR')
    assert timeout is None or isinstance(timeout, float)
    '''
    Generator object. will read and yield messages from new_socket
    if timeout==True, may yield None objects. This allows the caller to regularly
    if
    '''
    unpacker = msgpack.Unpacker()
    sock.settimeout(timeout)
    try:
        while True:
            try:
                x = sock.recv(1)
                if x == '':
                    debug_print('socket dead!')
                    return
                unpacker.feed(x)
                for package in unpacker:
                    yield Message.deserialize(package)
            except socket.timeout:
                if timeout:
                    yield MessageError.TIMEOUT
    except GeneratorExit:
        debug_print('generator dieded')
        return
    except Exception:
        yield MessageError.CRASH
        return


def write_many_msgs_to(socket, msg_iterable):
    packer = msgpack.Packer()
    all_went_perfectly = True
    try:
        for msg in msg_iterable:
            if not isinstance(msg, Message):
                debug_print('BAD. attempting to write_msg_to:', msg)
            else:
                debug_print('try out --> msg', msg, 'to socket', socket)
            my_file = StringIO()
            my_file.write(packer.pack(msg.serialize()))
            my_file = StringIO(my_file.getvalue())
            # tot_bytes = len(my_file.buf)
            sent_now = 1
            while sent_now != 0:  # 0 means send done
                try:
                    sent_now = socket.send(my_file.read(256))
                except:
                    all_went_perfectly = False
    except:
        all_went_perfectly = False
    return all_went_perfectly

def write_msg_to(socket, msg):
    if not isinstance(msg, Message):
        debug_print('BAD. attempting to write_msg_to:', msg)
    else:
        debug_print('out --> msg', msg, 'to socket', socket)
    '''
    send the given msg into the socket
    returns True if writing completes
    '''
    my_file = StringIO()
    packer = msgpack.Packer()
    my_file.write(packer.pack(msg.serialize()))
    my_file = StringIO(my_file.getvalue())
    # debug_print(vars(my_file))
    tot_bytes = len(my_file.buf)
    sent_now = 1
    to_send = tot_bytes
    while sent_now != 0:  # 0 means send done
        try:
            sent_now = socket.send(my_file.read(to_send))
            to_send -= sent_now
            if to_send == 0:
                return True
        except:
            return False
    return True
