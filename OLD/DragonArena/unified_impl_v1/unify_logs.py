import glob
import os
import heapq
out_file = 'logs_unified.log'
if os.path.exists(out_file):
    print(out_file, ("ALREADY EXISTS! Clear it first and ensure these "
                     "logs are the ones you intended!"))
    exit(1)
use_files = list(glob.glob("*.log"))
if out_file in use_files:
    use_files.remove(out_file)
print 'used: ', use_files
lines = heapq.merge(*[[ln.rstrip() for ln in open(f)]
                    for f in use_files])
with open(out_file, 'w') as out_f:
    count = 0
    for line in lines:
        out_f.write(line)
        out_f.write('\n')
        count += 1
print 'wrote', count, 'lines'
