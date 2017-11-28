import threading, msgpack, time, json
import socket
from StringIO import StringIO
socket.setdefaulttimeout(1.0) #todo experiment with this


'''
messages are stored and sent using integers in the header field
this is for compactness. For readibility, the following two
structures allow mapping back and forth:
    int2header[<int>] ==> <str>
    header2int[<str>] ==> <int>

'''
int2header = ['PING', 'C2S_HELLO', 'S2C_WELCOME', 'S2S_HELLO', 'S2S_WELCOME', 'S2S_SYNC_REQ', 'M_S2S_SYNC_REPLY']
header2int = {v: k for k,v in enumerate(int2header)}

'''
Each Message instance represents an instance of any network message
'''
class Message:
    def __init__(self, msg_header, sender, args):
        assert isinstance(msg_header, int) and msg_header in range(0, len(int2header))
        assert isinstance(sender, int)
        assert isinstance(args, list)
        self.msg_header = msg_header
        self.sender = sender
        self.args = args

    def same_header_as(self, other):
        if isinstance(other, Message):
            self.msg_header == other.msg_header
        else: return False

    def __eq__(self, other):
        if isinstance(other, Message):
            return self.msg_header == other.msg_header\
                and self.sender == other.sender\
                and self.args == other.args
        else: return False


    def serialize(self):
        return (self.msg_header, self.sender, self.args)

    @staticmethod
    def deserialize(serialized_msg):
        msg_header = serialized_msg[0]
        sender = serialized_msg[1]
        args = serialized_msg[2]
        assert isinstance(msg_header, int)
        assert isinstance(sender, int)
        assert isinstance(args, list)
        return Message(msg_header, sender, args)

    def __repr__(self):
        print('header', self.msg_header)
        assert self.msg_header >= 0 and self.msg_header < len(int2header)
        return 'Message::' + int2header[self.msg_header] + ' from ' \
            + str(self.sender) + ' with args:' + str(self.args)


'''
Predefined messages
#TODO check the protocol
maybe simplify? idk
'''
M_PING = Message(header2int['PING'],-1,[]) # just nonsense for now. works as long as they are unique
M_C2S_HELLO = Message(header2int['C2S_HELLO'],-1,[])
def M_S2C_WELCOME(s_id):
    return Message(header2int['S2C_WELCOME'], s_id,[])
def M_S2S_HELLO(s_id):
    return Message(header2int['S2S_HELLO'],s_id,['server_secret_key_u433hfu4g'])
M_S2S_WELCOME = Message(header2int['S2S_WELCOME'],-1,[])
def M_S2S_SYNC_REQ(s_id):
    return Message(header2int['S2S_SYNC_REQ'], s_id, [])
def M_S2S_SYNC_REPLY(s_id, serialized_state):
    return Message(header2int['S2S_SYNC_REPLY'], s_id, [serialized_state])


def read_msg_from(socket, timeout=False):
    assert isinstance(timeout, bool)
    '''
    attempt to read a Message from the given socket
    may return None if timeout==True
    '''
    unpacker = msgpack.Unpacker()
    while True:
        try:
            x = socket.recv(1)
            if x == '':
                print('socket dead!')
                return None
                #connection closed!
            unpacker.feed(x)
            for package in unpacker:
                return Message.deserialize(package)
        except:
            if timeout:
                return None

def read_many_msgs_from(socket, timeout=True):
    assert isinstance(timeout, bool)
    '''
    Generator object. will read and yield messages from new_socket
    if timeout==True, may yield None objects. This allows the caller to regularly
    if
    '''
    unpacker = msgpack.Unpacker()
    while True:
        try:
            x = socket.recv(256)
            if x == '':
                print('socket dead!')
                return
                #connection closed!
            unpacker.feed(x)
            for package in unpacker:
                yield Message.deserialize(package)
        except:
            if timeout:
                yield None

def write_many_msgs_to(socket, msg_iterable):
    packer = msgpack.Packer()
    all_went_perfectly = True
    try:
        for msg in msg_iterable:
            assert isinstance(msg, Message)
            myfile = StringIO()
            myfile.write(packer.pack(msg.serialize()))
            myfile = StringIO(myfile.getvalue())
            tot_bytes = len(myfile.buf)
            sent_now = 1
            while sent_now != 0: # 0 means send done
                try: sent_now = socket.send(myfile.read(256))
                except: all_went_perfectly = False
    except:
        all_went_perfectly = False
    return all_went_perfectly

def read_first_message_matching(socket, func,  timeout=True, max_msg_count=-1):
    assert isinstance(timeout, bool)
    assert isinstance(max_msg_count, int)
    assert callable(func)

    msg_count = 0
    start_time = time.time()
    for msg in read_many_msgs_from(socket, timeout=timeout):
        msg_count += 1
        if func(msg) == True:
            return msg
        elif msg_count == max_msg_count or time.time() - start_time >=  timeout:
            return None



def write_msg_to(socket, msg):
    assert isinstance(msg, Message)
    '''
    send the given msg into the socket
    returns True if writing completes
    '''
    myfile = StringIO()
    packer = msgpack.Packer()
    myfile.write(packer.pack(msg.serialize()))
    myfile = StringIO(myfile.getvalue())
    #pprint(vars(myfile))
    tot_bytes = len(myfile.buf)
    sent_now = 1
    while sent_now != 0: # 0 means send done
        try: sent_now = socket.send(myfile.read(256))
        except: return False
    return True
