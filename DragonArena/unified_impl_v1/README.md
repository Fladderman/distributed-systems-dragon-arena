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


# Features
servers tick in lockstep.
a newcomer server will:
    stop lockstep,
    handshake with all servers,
    receive the latest version,
    join and resume lockstep.
if a server crashes:
    other servers continue without them,
    their clients will:
        rejoin the game with another server,
        keep their knight.
if a client crashes:
    their server de-spawns their knight.
if a server somehow falls behind:
    it will lazily request an update from someone else,
    and it will accept the fresher state when it comes.
