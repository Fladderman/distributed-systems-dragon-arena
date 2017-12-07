from multiprocessing import Process
import subprocess
import time
import das_game_settings
#Warning set the visualizers to false for no errors!
TIME_REDUCE = 100000
TIME_CONSTANT = 0.1 #add this st time.sleep() is not there for nothing

class GTAClient():

    def __init__(self,id,timestamp,lifetime):
        self.id = id
        self.timestamp = timestamp
        self.lifetime = lifetime

    def __repr__(self):
        return repr((self.id, self.timestamp, self.lifetime))


def parseLine(line):
    line = line.strip().split(',')
    if len(line) == 6:
        id = int(line[0])
        timestamp = float(line[1])
        lifetime = float(line[2])
    return GTAClient(id,timestamp,lifetime)

processes = []

def new_command(args, index):
    print('START', index)
    subprocess.check_output(args)
    print('END', index)

def new_process(args, t=0):
    assert isinstance(args, list)
    index = len(processes)
    time.sleep(t+TIME_CONSTANT)
    p = Process(target=new_command, args=(args,index))
    p.start()
    processes.append(p)
    return p

def join_all(kill=False):
    if kill:
        for p in processes:
            p.terminate()
    for p in processes:
        p.join()
    print('killed')


def server_start_args(server_id, starter=False):
    assert 0 <= server_id <= das_game_settings.num_server_addresses
    assert isinstance(server_id, int)
    assert isinstance(starter, bool)
    return ['python2', './server_start.py', str(server_id), str(starter)]


def client_start_args(player_type_arg='bot'):
    assert player_type_arg in {'bot', 'ticker', 'human'}
    return ['python2', './client_start.py', player_type_arg]

def check_timeout(data, kill=False):
    while True:
        for proc,startTime,lifeTime in data:
            if time.time() - startTime >= lifeTime:
                print "proc %s \n" %proc
                print time.time() - startTime
                print lifeTime
                proc.terminate()
                print('Client disconnect')
                data = filter(lambda x: x[0] != proc, data)
            if not data:
                for p in processes:
                    p.terminate()
                print('No more clients, killed servers too')
                break
            if kill:
                for p in processes:
                    p.terminate()
                print('Killed integrated from join_all')
                break
        time.sleep(5)


if __name__ == '__main__':
    new_process(server_start_args(0, starter=True))
    new_process(server_start_args(1))
    new_process(server_start_args(2))


    file = open('WoT_Edge_Detailed','r') #alternative SC2
    #file = open('SC2_Edge_Detailed','r')
    lines = file.readlines()
    clientList = []
    c=6
    while(c<11): # #106 for 0-99
        clientList.append(parseLine(lines[c]))
        c += 1

    clientList = sorted(clientList, key = lambda client: client.timestamp)
    timestampCounter = clientList[0].timestamp #first value of the sorted list
    clientProcesses = []
    clientTimeAlive = []
    clientStartTime = []
    for sortedClient in clientList:
        clProcess = new_process(client_start_args(), (sortedClient.timestamp - timestampCounter)/TIME_REDUCE)
        clientStartTime.append(time.time())
        timestampCounter = sortedClient.timestamp
        clientProcesses.append(clProcess)
        clientTimeAlive.append(sortedClient.lifetime/10) #make it faster for own testing
    checkTimeoutData = zip(clientProcesses, clientStartTime, clientTimeAlive)
    check_timeout(checkTimeoutData)
    #join_all()
