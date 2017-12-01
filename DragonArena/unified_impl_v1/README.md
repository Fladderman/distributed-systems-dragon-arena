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
    where `$1` is in {'bot', 'human', 'ticking'}



# Overview
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

# Features
## Consistency:
	quite strong consistency
	players can never get an incorrect state (only stale)
	clients do not make any predictions* (no dead-reckoning)*
	servers do not permit clients until they are certain they are up-to-date
	servers wait for each other before proceeding

## Replication & Fault-tolerance:
	if every server but one crashes, the game can continue
	with a speedy connection, no player may even notice
	Every server logs every message in, and every significant connection event

## Robustness & Security:
	Client expressiveness is minimized
		("I attack Bob" instead of "I, as player X attack Bob for 5 damage)

	Clients can send incorrect/ messages. Servers discard incorrect messages
	game can function correctly with dynamic number of servers
		caveat: you have to set an upper-bound ahead of time.
		a higher bound imposes a tiny performance cost at server start-up

## Transparency
	Clients rejoin automatically if their server crashes. they may not even notice
