import cProfile,pstats,io,time,json
from b208_frozen import frozen
n,i,p=frozen();profile=cProfile.Profile();began=time.monotonic()
print('POSE',i[2],'TASKS',[(k,a.reason,a.tries,a.failures) for k,a in p.attempts.items()],flush=True)
try:
 c=profile.runcall(n._metric_select,i,p,.3)
 print('CANDIDATES',[(x.task_id,x.x,x.y,x.yaw) for x in c],flush=True)
except Exception as e:print('ERROR',str(e),flush=True)
print('ELAPSED',time.monotonic()-began,'RANK',n._frontier_rank_stats,flush=True)
stream=io.StringIO();pstats.Stats(profile,stream=stream).sort_stats('cumulative').print_stats(35);print(stream.getvalue())
