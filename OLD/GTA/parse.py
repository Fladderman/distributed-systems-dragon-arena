
class GTAClient():

    def __init__(self,id = 0, timestamp = 0.0, lifetime = 0.0):
        self.id = id
        self.timestamp = timestamp
        self.lifetime = lifetime

#    def set_all(self, id, timestamp, lifetime):
#        self.id = id
#        self.timestamp = timestamp
#        self.lifetime = lifetime

    def get(self):
        return self.id, self.timestamp, self.lifetime

    def __str__(self):
        return '(' + str(self.id) + ',' + str(self.timestamp) + ',' + str(self.lifetime) + ')'



def parseLine(line):
    line = line.strip().split(',')
#    client = GTAClient()
    if len(line) == 6:
        id = int(line[0])
        timestamp = float(line[1]) #or time in seconds
        lifetime = float(line[2])
#        client.set_all(id,timestamp,lifetime)
	client = GTAClient(id,timestamp,lifetime)
        print str(client)
    return GTAClient


file = open('WoT_Edge_Detailed','r') #alternative SC2
#file = open('SC2_Edge_Detailed','r')
lines = file.readlines()
clientList = []
c=6
while(c<106): # 0-99
    clientList.append(parseLine(lines[c]))
    c += 1
	
