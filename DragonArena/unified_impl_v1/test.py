import messaging
import msgpack
from StringIO import StringIO

# x = "[18, [1, 0], ['l']]"
x = '[]'
unpacker = msgpack.Unpacker()
unpacker.feed(x)

for package in unpacker:
    print(package)
# print(z)
# y = messaging.Message.deserialize(x)
# print(y)
