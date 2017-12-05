from multiprocessing import Process
import subprocess
import time
import das_game_settings

TIME_REDUCE = 100000

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

def new_process(args):
    assert isinstance(args, list)
    index = len(processes)
    time.sleep(0.1)
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

if __name__ == '__main__':
    new_process(server_start_args(0, starter=True))
    new_process(server_start_args(1))
    new_process(server_start_args(2))
    # new_process(client_start_args()) #proc 4
    # new_process(client_start_args()) #
    # new_process(client_start_args())
    # new_process(client_start_args())
    # new_process(client_start_args())
    # new_process(client_start_args())
    # new_process(client_start_args())
    file = open('WoT_Edge_Detailed','r') #alternative SC2
    #file = open('SC2_Edge_Detailed','r')
    lines = file.readlines()
    clientList = []
    c=6
    while(c<106): # 0-99
        clientList.append(parseLine(lines[c]))
        c += 1

    clientList = sorted(clientList, key = lambda client: client.timestamp)
    timestampCounter = 1354482240.312 #kinda hardcoded first value of the list
    clientProcesses = []
    clientTimeAlive = []
    for sortedClient in clientList:
        time.sleep((sortedClient.timestamp - timestampCounter)/TIME_REDUCE)
        clProcess = new_process(client_start_args())
        start_time = time.time()  #and kill when time.time() - start_time == lifetime?
        timestampCounter = sortedClient.timestamp
        clientProcesses.append(clProcess)
        clientTimeAlive.append(sortedClient.lifetime)
    print zip(clientProcesses, clientTimeAlive)
    join_all()
