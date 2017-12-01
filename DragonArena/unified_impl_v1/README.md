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

== 1. A client (re)joins

Either the client is new, or the client rejoins after a server crash.

The client is new:

- The client pings all existing servers, and sorts the servers by latency.
- The client requests the first server in this order whether it can join. It
  includes a client-local secret/salt in the request.
  Two cases:
    1. The client is accepted by the server.
       The server responds with:
         - A _provably_ non-colliding identifier ID.
         - A hash generated using the client's IP, the client's secret and
           its assigned ID. (For rejoining, discussed later.)
         - The game state, which the client stores locally. The player will
           have been randomly* spawned on this game state.
    2. The client is rejected by the server.
       There can be two reasons:
         - The game is full. The client can manually retry later.
           (The bots will use exponential back-off.)
         - The game is not full, but the server's workload is high relative
           to that of other servers. The client retries the procedure with
           the next server in the sequence. At some point it will succeed,
           since not all servers can have relatively high workload.

The client rejoins _after a server crash_:

The client's token will still be on the board. The protocol is similar to
above, except that now the client also sends the hash and its ID. The server
can verify that the token belongs to that player, and it accepts the client
by linking the ID to its IP.

== 2. A client crashes

Once a server fails to communicate with a client, it treats it like a crash.
Its knight will be killed off and and its IP forgotten. When the client
rejoins, it is treated like a new player.

A possible future improvement would be to implement a grace period.


== 3. A server joins

Any server that joins must be synchronized with the lockstep.

- Suppose Server S wants to join. Its id will be the max of all existing server
  ids plus one. (When?)
- S asks the server with the lowest id T to integrate it in the lockstep.
- T will integrate S as follows:
    - In the request exchange phase, T will send its requests, but will not
      send any DONEs. This ensures that all other servers are waiting at the
      barrier.
    - Once T has received DONEs from all other servers, it computes the new
      game state, and sends it to S. It then waits for an ack from S.
    - Upon receiving the game state (or before?), S will establish communication with all
      other servers. When it has done so, it sends the ack to T.
    - T sends a DONE to all waiting servers (also S?), releasing them from the barrier.
    - The servers now proceed in lockstep.

T handles only one server join per tick, so that it is ensures that the servers
at all times form a completely connected graph.

== 4. A server crashes

We assume server-server links do not fail. So if a server S loses communication
with another server T, T has crashed. S will discard any requests from T that
have not been followed by a DONE, and it will no longer consider T to be part
of the lockstep.

Inconsistency may result if some servers have result a DONE, while others have
not. This corner case is dealt with as follows:
  - Every n ticks, servers hash their game state, and exchange it with other
    servers. If hashes differ, there is an inconsistency. The owner of
    the largest hash will be considered the owner of the consistent game state,
    and servers will request it.
  - If hashes collide, it is not a big issue. Most likely the inconsistency
    will be detected in the next cycle.
This protocol will also correct many edge cases that have not been found in the
analysis.













# Features
## Consistency: 
	quite strong consistency
	players can hardly ever get an incorrect state (only stale)
	clients do not make any predictions* (no dead-reckoning)*
	servers do not permit clients until they are certain they are up-to-date
	servers wait for each other before proceeding
	= servers hash their game state every n ticks, share small prefix of hash.
	  if there is inconsistency, servers take over the game state that generated
	  largest hash prefix (to implement).

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

