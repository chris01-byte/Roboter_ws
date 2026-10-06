import sys,time,json,cProfile,pstats
sys.path.insert(0,'/evidence/ap06-repo/tools/simulation')
from ap06_world import World
import numpy as np
for label,velocity in [('zero',[0.,0.]),('denormal',[1e-323,1e-323]),('tail',[1e-12,1e-12])]:
 w=World(.68,[-1.519861,-.861076,-2.142694]);w.integrate([0.,0.],.01);w.velocity[:]=velocity
 p=cProfile.Profile();began=time.monotonic()
 def work():
  for _ in range(500):w.integrate([0.,0.],.01)
 p.runcall(work)
 print(label,'elapsed',time.monotonic()-began,'velocity',w.velocity.tolist(),flush=True)
 pstats.Stats(p).sort_stats('cumulative').print_stats(8)
