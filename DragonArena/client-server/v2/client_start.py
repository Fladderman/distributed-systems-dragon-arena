import client, client_player

BOT_PLAYER = True

player = client_player.BotPlayer() if BOT_PLAYER else client_player.HumanPlayer()

client_0 = client.Client(player)
client_0.main_loop()

'''
Each client runs this script
Client object connects on __init__()

'''
