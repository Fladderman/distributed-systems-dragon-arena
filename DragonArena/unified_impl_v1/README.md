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

ILLUSTRATING FUNCTIONALITY IN A COMPLETELY STABLE STATE

Suppose we have:
  - k servers
  - each server with some clients
  - all the game states (at each node) are consistent
  - the servers are about to start tick n

- The servers swap their local buffers. This fixes all the requests that
  must be processed for THEIR clients for tick n.
- Servers flood these requests to all other servers in the lockstep. Once
  a server i has sent all its requests to server j, it sends a DONE to j.
- Once a server has received a DONE from all servers, it has all the requests R
  that need to be processed in that tick, stored IN UNSPECIFIED ORDER.
- For consistency, a server sorts R based on a well-defined total order over
  messages, yielding R'. R' is then shuffled _using a seed completely defined
  by the game state_, yielding a seemingly random* order of messages R''. Since
  game states are consistent, every server will generate R''.
- The server attempts to apply each valid message from R'' to its game state,
  and logs the result. Invalid messages are not processed, but are logged.
  A well-defined number of dragon attacks are then applied. Since servers'
  game states are consistent and they process messages in the same order, the
  outcome will also be consistent.
- The server sends the new game state to all its clients, who can then use it
  to make new requests.
- The server sleeps until it is time to start processing tick n+1.

* explain consistent randomness

EVENTS THAT DISTURB STABILITY

== 1. A client joins





== 2. A client crashes



== 3. A server joins



== 4. A server crashes













# Features
## Consistency:
	quite strong consistency
	players can never get an incorrect state (only stale)
	clients do not make any predictions* (no dead-reckoning)*
	servers do not permit clients until they are certain they are up-to-date
	servers wait for each other before proceeding
	= servers hash their game state every n ticks, share small prefix of hash.
	  if there is inconsistency, servers take over the game state that generated
	  largest hash prefix (to implement). FOR CORNER CASES TO BE DISCUSSED

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
	Upon reconnecting after server failure, clients need to prove their identity.
	  Requires no server-server communication: a server-side hash and client-side secret is used.
	New server connections are not trusted by default: they have to prove their identity.
	The server hierarchy is flat: no single server is a point of failure

## Transparency
	Clients rejoin automatically if their server crashes. they may not even notice

## Scalability
    Identifier protocol provably gives no collisions for any number of {servers, clients, dragons}.
    Independent dynamic load balancing per server: servers share loads at set points, and accept/refuse clients whenever
    Geo scalability: clients will ping servers, and try the one with the best latency first

