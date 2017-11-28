import client, client_player
import sys

def make_player():
    if len(sys.argv) == 2:
        if sys.argv[1] == "human":
            print('starting human client')
            return client_player.HumanPlayer()
        elif sys.argv[1] == "bot":
            print('starting bot client')
            return client_player.BotPlayer()
    raise "Please run with 1 arg, either 'bot' or 'human'"

client_0 = client.Client(make_player())
print('client starter init complete')
client_0.main_loop()
print('client starter main loop complete')
