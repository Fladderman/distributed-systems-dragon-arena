import glob
import os
import heapq
import sys
assert len(sys.argv) == 2

def ln_split(ln):
	tm = ln[:16]
	num = ln[21:24]
	rest = ln[28:]
	return tm, num, rest

class Crawler:
	starts = {0:0}
	gaps = []
	
	def __init__(self, path):
		self.file = open(path, 'rb+')
		# TODO
		self.starts = dict()
		while True:
			ln = f.readline()
			if not ln:
				return
			tm, num, rest = ln_split(ln)
			if rest.startswith("ENTERING TICK"):
				tid = int(rest[14:].strip())
				#print('got', tid)
				starts[tid] = f.tell()


	'''
	def prep(f):
		prev_tick = 0
		while True:
			ln = f.readline()
			if not ln:
				return
			tm, num, rest = ln_split(ln)
			if rest.startswith("ENTERING TICK"):
				tid = int(rest[14:].strip())
				#print('got', tid)
				starts[tid] = f.tell()
				if tid != prev_tick+1:
					gaps.append((prev_tick+1,tid-1))
				prev_tick = tid
	'''

	def print_tick(self, pos):
		self..seek(pos)
		while True:
			ln = f.readline()
			if not ln:
				break
			tm, num, rest = ln_split(ln)
			if rest.startswith("ENTERING TICK"):
				break
			print tm, num, rest.strip()		
			
	def gap_around(tick):
		for g in gaps:
			if g[0] <= tick <= g[1]:
				tick
		return None
		
	def goto(f, tick_id):
		if tick_id in starts:
			print '-'*21, ' '*3, 'TICK', tick_id, '-'*15
			print_tick(f, starts[tick_id])
		else:
			gap = gap_around(at_tick)
			if gap is None: print('END OF FILE!')
			else:           print ('gap', gap[0], '-', gap[1])


	at_tick = 0
	with open(sys.argv[1], 'rb+') as f:
		prep(f)
		print 'ticks', min(starts.keys()), '-', max(starts.keys())
		if not starts:
			print 'NO TICKS FOUND!'
			exit(1)
		goto(f, min(starts.keys()))
		while True:
			input = raw_input("$ ")
			s_input = input.split(" ")
			if s_input[0] == 'd':
				at_tick += 1
				goto(f, at_tick)
			elif s_input[0] == 'u':
				if at_tick > 0:
					at_tick -= 1
					goto(f, at_tick)
				else:
					print 'at top!'
			elif s_input[0] == 'goto':
				at_tick = int(s_input[1])
				goto(f, at_tick)
			elif s_input[0] == 'start':
				at_tick = min(starts.keys())
				goto(f, at_tick)
			elif s_input[0] == 'end':
				at_tick = max(starts.keys())
				goto(f, at_tick)
			else:
				print '?? wut'