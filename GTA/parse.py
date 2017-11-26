
class GTAClient():

    def __init__(self):
        self.id = 0
        self.timestamp = 0.0
        self.lifetime = 0.0

    def set_all(self, id, timestamp, lifetime):
        self.id = id
        self.timestamp = timestamp
        self.lifetime = lifetime

    def get(self):
        return self.id, self.timestamp, self.lifetime



def parseLine(line):
    line = line.strip().split(',')
    client = GTAClient()
    if len(line) == 6:
        id = int(line[0])
        timestamp = float(line[1]) #or time in seconds
        lifetime = float(line[2])
        client.set_all(id,timestamp,lifetime)
        print client.get()
    return GTAClient


file = open('WoT_Edge_Detailed','r') #alternative SC2
#file = open('SC2_Edge_Detailed','r')
lines = file.readlines()
clientList = []
c=6
while(c<106): # 0-99
    clientList.append(parseLine(lines[c]))
    c += 1
