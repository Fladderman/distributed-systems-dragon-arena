import glob, os, heapq
out_file = 'logs_unified.log'
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
