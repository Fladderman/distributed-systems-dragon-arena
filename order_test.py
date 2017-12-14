from messaging import listify
import messaging
from messaging import Message, header2int
import random


random.seed(11)

reqs = [
	Message(header2int['R_ATTACK'], (0,3), [[-1, 9]]),
	Message(header2int['R_MOVE'], (2,3), [3]),
	Message(header2int['R_MOVE'], (1,14), [2]),
	Message(header2int['R_MOVE'], (0,10), [0]),
	# Message(header2int['SPAWN'], 2, [(2,16)]),
	Message(header2int['SPAWN'], 2, [[2,16]]),
	Message(header2int['R_ATTACK'], (1,10), [[-1, 4]]),
	Message(header2int['R_MOVE'], (0,10), [0]),
	Message(header2int['R_ATTACK'], (2, 7), [[-1, 8]]),
]

random.shuffle(reqs, lambda: random.random())

reqs.sort()
# random.shuffle(reqs, lambda: random.random())

for r in reqs:
	print(r)


'''
Fri 20:17:21.498 0   Message Message::R_ATTACK from (0, 3) with args:[[-1, 9]] from (0, 3) was processed successfully. DAS feedback: Knight {0|3} attacks Dragon {-1|9} for 1 damage, reducing its hp from 974 to 973.
Fri 20:17:21.498 0   Message Message::R_MOVE from (2, 13) with args:[3] from (2, 13) was processed successfully. DAS feedback: Knight {2|13} moves down from (1, 10) to (2, 10).
Fri 20:17:21.498 0   Message Message::R_MOVE from (1, 14) with args:[2] from (1, 14) was processed successfully. DAS feedback: Knight {1|14} moves left from (1, 20) to (1, 19).
Fri 20:17:21.498 0   Message Message::R_MOVE from (0, 10) with args:[0] from (0, 10) was processed successfully. DAS feedback: Knight {0|10} moves right from (13, 5) to (13, 6).
Fri 20:17:21.499 0   Message Message::SPAWN from 2 with args:[[2, 16]] from 2 was processed successfully. DAS feedback: Knight {2|16} spawns at location (24, 11) with 999 hp and 1 ap.

Fri 20:17:21.499 0   Message Message::R_ATTACK from (1, 10) with args:[[-1, 4]] from (1, 10) was processed successfully. DAS feedback: Knight {1|10} attacks Dragon {-1|4} for 1 damage, reducing its hp from 788 to 787.
Fri 20:17:21.499 0   Message Message::R_MOVE from (1, 11) with args:[3] from (1, 11) was processed successfully. DAS feedback: Knight {1|11} wants to move down from (21, 18), but it is blocked by Knight {2|8}.
Fri 20:17:21.499 0   Message Message::R_ATTACK from (2, 7) with args:[[-1, 8]] from (2, 7) was processed successfully. DAS feedback: Knight {2|7} attacks Dragon {-1|8} for 1 damage, reducing its hp from 959 to 958.
Fri 20:17:21.499 0   Message Message::R_ATTACK from (0, 1) with args:[[-1, 2]] from (0, 1) was processed successfully. DAS feedback: Knight {0|1} attacks Dragon {-1|2} for 1 damage, reducing its hp from 967 to 966.
Fri 20:17:21.499 0   Message Message::R_MOVE from (1, 15) with args:[1] from (1, 15) was processed successfully. DAS feedback: Knight {1|15} moves up from (10, 8) to (9, 8).
Fri 20:17:21.499 0   Message Message::R_ATTACK from (2, 1) with args:[[-1, 5]] from (2, 1) was processed successfully. DAS feedback: Knight {2|1} attacks Dragon {-1|5} for 1 damage, reducing its hp from 810 to 809.

'''