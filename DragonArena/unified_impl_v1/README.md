# How to use

To try out the system:
    as the server, run:
    ```
    $ python2 ./server_start $1
    ```
    where `$1` is the 'index' of the server. eg $1==0

    separately, as the client, run
    ```
    $ python2 ./client $1
    ```
    where `$1` is in {'bot', 'human'}


# Views:
    Players:
        main loop. has access only to two objects:
        1. protected game state
        2. protected outgoing request queue
        players loop, check the values of (1), and push requests to (2)
        updates come in and change (1) as if by magic, wow

    Clients:
        will first try to connect to a server
        once connected, will synchronize and get a game state
        client protects game state with a ProtectedGameState wrapper
        will spawn a thread which start the PLAYER up
        clients and players run autonomously, and are connected by:
        1. protected request queue (player produces, client consumes)
        2. protected game state (player views, client modifies)
        client splits and enters 2 loops:
        1. get updates from server, apply to game state
        2. drain player update requests and forward them to the server


# whats in
pop-up thread server
servers start, connect to each other (kinda)
`Message` class with data fields
Message functions for serialization / deserialization
'transparent' API for reading/writing messages to socket (only used by Server, Client classes)
protected queue datastructure with threadsafe functions for `push, pop, drain, push_all`
`Player` abstract class with subclasses: {`BotPlayer`, `HumanPlayer`}
server object that will accept new clients and listen for Messages
clients attempting to circularly connect to a server, moving on to the next when one fails



# whats not in yet
servers synchronizing the starting game state
Axel/Roy's Game State object in all its glory
proper message protocol
clients using PING time to sort their list of servers in descending 'goodness'
servers keeping track of client capacity and disabling new client joins
100% complete server-server joins
server-server state synchro
translation function from Message to action on game state (and back)
