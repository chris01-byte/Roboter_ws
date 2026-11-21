import json,time,cProfile,pstats,io
from b215_frozen import frozen
n,i,p=frozen()
print('SCAN',n._metric_scan_geometry_ready(i),'POSE',i[2],flush=True)
profile=cProfile.Profile();start=time.monotonic()
try:print('DECISION',profile.runcall(n._metric_start_decision,i,p,.3,True),flush=True)
except Exception as e:print('ERROR',str(e),flush=True)
print('TIME',time.monotonic()-start,flush=True)
s=io.StringIO();pstats.Stats(profile,stream=s).sort_stats('cumulative').print_stats(25);print(s.getvalue())
