# How to use
To try out the system:



1. Configure `das_game_settings.py`. This file contains many settings, but most importantly:
  1. Set `server_addresses` to match the (ip/port) of each server machine you intend to use. This is how the clients will find you and how servers will find one another.
  1. Set `client_visualizer` and `server_visualizer` to 'True' For a graphical representation of the game state. This is the best way to get a high-level view of what's going on inside each machine.
  1. Set `logging_level` to 'logging.DEBUG' for the most complete logs

1. If you intend to read logs to make sense of the game you're about to start, ensure no existing files matching `*.log` exist in this directory. The logger will potentially append them together and you will mix data from different runs.

1. Start any _valid_ combination of machines. Note, you can also make use of some other script to simulate the behaviour defined here (eg, `run.py`)

  _valid_ just means ONE server must create the game state. (ie its arg2 must be 'True')
  1.  Servers are started with `$ python2 ./server_start $1 $2`, where `$1` is a _server_id_ (0, 1, ...). These correspond with the contents of `server_addresses` in the previous step. Make sure you only boot up at most one server for each index. `$2` should be 'False' for all servers, except for one, which gets 'True'. This determines which server is in charge of initializing the game state.
  1. Clients are started with `$ python2 ./client $1`. `$1` is a string from {'bot', 'human', 'ticking'}, and defines which player interface is connected to the server module. For our purposes, always use 'bot' to test actual gameplay, and 'ticking' if you want a knight that just spams network messages.

1. Once the system has shut down, run `$ python2 ./unify_logs.py`. This will sort all other `*.log` files into one big log called `logs_unified.log` in accordance to their timestamps. Reading this log should give a fairly detailed understanding of the game's run.


# Overview
- servers tick in lockstep.
- a newcomer server will:
  - stop lockstep,
  - handshake with all servers,
  - receive the latest version,
  - join and resume lockstep.
- if a server crashes:
  - other servers continue without them,
  - their clients will:
  - rejoin the game with another server,
  - keep their knight.
- if a client crashes:
  - their server de-spawns their knight.
- if a server somehow falls behind:
  - it will lazily request an update from someone else,
  - and it will accept the fresher state when it comes.

# ILLUSTRATING FUNCTIONALITY IN A COMPLETELY STABLE STATE
Suppose we have:
  - k servers
  - each server with some clients
  - all the game states (at each node) are consistent
  - the servers are about to start tick n

1. The servers swap their local buffers. This fixes all the requests that
   must be processed for THEIR clients for tick n.
1. Servers flood these requests to all other servers in the lockstep. Once
   a server i has sent all its requests to server j, it sends a DONE to j.
1. Once a server has received a DONE from all servers, it has all the requests R
   that need to be processed in that tick, stored IN UNSPECIFIED ORDER.
1. For consistency, a server sorts R based on a well-defined total order over
   messages, yielding R'. R' is then shuffled _using a seed completely defined
   by the game state_, yielding a seemingly random* order of messages R''. Since
   game states are consistent, every server will generate R''.
1. The server attempts to apply each valid message from R'' to its game state,
   and logs the result. Invalid messages are not processed, but are logged.
   A well-defined number of dragon attacks are then applied. Since servers'
   game states are consistent and they process messages in the same order, the
   outcome will also be consistent.
1. The server sends the new game state to all its clients, who can then use it
   to make new requests.
1. The server sleeps until it is time to start processing tick n+1.

* explain consistent randomness

# EVENTS THAT DISTURB STABILITY

## 1. A client (re)joins

Either the client is new, or the client rejoins after a server crash.

### The client is new:

- The client pings all existing servers, and sorts the servers by latency (ascending).
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
    2. The client is refused by the server.
       There can be two reasons:
         - The game is full. The client will retry after backing off.
             (capped exponential back-off.)
         - The game is not full, but the server's workload is high relative
           to that of other servers. The client retries the procedure with
           the next server in the sequence. At some point it will succeed,
           since not all servers can have relatively high workload.

### The client rejoins _after a server crash_:
The client's token will still be on the board. The protocol is similar to
above, except that now the client also sends the hash and its ID. The server
can verify that the token belongs to that player, and it accepts the client
by linking the ID to its IP, the game key, etc.

## 2. A client crashes
Once a server fails to communicate with a client, it treats it like a crash.
Its knight will be killed off and its IP forgotten. When the client
rejoins, it is treated like a new player.

A possible future improvement would be to implement a grace period.


## 3. A server joins
Any server that joins must become synchronized with the lockstep.

Consider a server S joining the game:
- Note, the ID of S is unique, as it is provided as an argument at start-up.
- S asks the server _with the lowest id_ T to integrate it in the lockstep
  (aka Synchronize it). S includes a server-secret key in the request.
- If T authenticates S as a server , T will synchronize S as follows:
    - In the request exchange phase, T will send its requests, but will not
      send any DONEs. This ensures that all other servers are waiting at the
      barrier.
    - Once T has received DONEs from all other servers, it computes the new
      game state, and sends it to S. It then waits for an ack from S.
    - Upon receiving the game state, S will establish communication with all
      other servers. When it has done so, it sends the ack to T.
    - T sends a DONE to all servers at the barrier, releasing them.
    - The servers now proceed in lockstep.

T handles only one server join per tick, so that it is ensures that the servers
at all times form a completely connected graph.

## 4. A server crashes
We assume server-server links do not fail (But servers can fail in entirety).
So if a server S loses communication with another server T, T has crashed.
S will discard any requests from T that have not been followed by a DONE,
and it will no longer consider T to be part of the lockstep.

The system does not distinguish between server join and server rejoin. Thus,
crashed servers can rejoin as described in the previous section.

Inconsistency may result if some servers have received a DONE from a server S,
while others have not. This corner case is dealt with as follows:
  - Every n ticks, servers hash their game state, and exchange this hash with
    each other. If hashes differ, there is an inconsistency. The owner of
    the largest hash will be considered the owner of the consistent game state.
    Servers that identify that another server is behind in ticks, or has a
    smaller hash, will push a game state update to that server. That server will
    assess incoming updates to see if it can benefit from them (in much the same
    way).
  - If hashes collide (which is highly unlikely), it is not a big issue.
    In subsequent rounds of n ticks, the hashes are unlikely to collide.
    Eventually the inconsistency will be detected. If n is chosen small enough,
    this is not a problem.
This protocol will also correct many edge cases that have not been found in the
analysis.

# Features
## Consistency:
1. quite strong consistency
1. players can hardly ever get an incorrect state (only stale)
1. clients do not make any predictions* (no dead-reckoning)*
1. servers do not permit clients until they are certain they are up-to-date
1. servers wait for each other before proceeding

## Replication & Fault-tolerance:
1. if every server but one crashes, the game can continue with a speedy
   connection, no player may even notice
1. Every server logs every message in, and every significant connection event
1. The server hierarchy is flat: no single server is a point of failure

## Robustness & Security:
1. Client expressiveness is minimized
		("I attack Bob" instead of "I, as player X attack Bob for 5 damage)
1. Clients can send incorrect/ messages. Servers discard incorrect messages
1. Upon reconnecting after server failure, clients need to prove their identity.
     Requires no server-server communication: a server-side hash and client-side
     secret is used.
1. New server connections are not trusted by default: they have to prove their
   identity.

## Transparency
1. Clients rejoin automatically if their server crashes.
   they may not even notice
1. Clients do not specify the server IP or etc., these are all chosen
   'under the hood'.

## Scalability
1. Identifier protocol provably gives no collisions for any number of
   {servers, clients, dragons}, joining in any order.
1. Independent dynamic load balancing per server: servers share load information
   periodically. They refuse clients when they deem themselves
   'significantly overburdened' relative to other servers.
1. The game can function correctly with changing number of servers
   caveat: One must set an upper-bound ahead of time.
   A higher bound necessitates a slower server join/rejoin

# Points of interest in code
1. `messaging.py` 'Messages' abstract over a network socket. Everything
   expressed using a formulated message. Game states etc. are serializable using
   msgpack module.
1. `das_game_settings.py` Users of the system can alter its behavior by changing
   values in this file. (eg server addresses, tick speed, HP values etc.)
1. `DragonArenaNew.py` Game logic. Used by both clients and servers. Supports
   functions for serialization, logging, hashing, etc.
1. `client_player.py` Interfaces with the client. Defines a knight's behavior.
   Which class you instantiate defines whether its a bot, human etc.
1. `server.py` Most messy, complex, verbose and confusing. Contains ticking
   logic, client management, logging, authentication etc.
