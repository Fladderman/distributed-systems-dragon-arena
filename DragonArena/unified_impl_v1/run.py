from multiprocessing import Process
import subprocess
import time
import das_game_settings

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

def kill_all_processes():
    for p in processes:
        p.terminate()
        p.join()
    print('killed')

def unify_clear_logs():
    import unify_logs

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
    # new_process(server_start_args(1))
    new_process(client_start_args())
    time.sleep(5.0)
    kill_all_processes()
    # unify_clear_logs()
