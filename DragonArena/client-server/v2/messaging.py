import threading, msgpack, time, json
import socket
from StringIO import StringIO
socket.setdefaulttimeout(1.0) #todo mess around

'''
Each Message class represents an instance of any network message
'''


int2header_list = ['PING', 'CLIENT_HELLO', 'SERV_WELCOME']
header2int = {v: k for k,v in enumerate(int2header_list)}

class Message:
    def __init__(self, msg_header, sender, args):
        assert isinstance(msg_header, int)
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
        str_header = '??header??' if self.msg_header not in int2header_list else int2header_list[self.msg_header]
        return (
            'Message::' + str_header + ' from '
            + str(self.sender) + ' with args:' + str(self.args)
        )

PING_MESSAGE = Message(header2int['PING'],-1,[]) # just nonsense for now. works as long as they are unique
CLIENT_HELLO = Message(header2int['CLIENT_HELLO'],-1,[])


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
                msg = Message.deserialize(package)
                return msg
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
                msg = Message.deserialize(package)
                yield msg
        except:
            if timeout:
                yield None


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
        try:
            sent_now = socket.send(myfile.read(256))
        except:
            # writing results in error
            return False
        # the number read doesn't seem to matter.
        # python is smart enough not to go out of bounds
    return True
