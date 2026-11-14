import sys
sys.path.insert(0,'/evidence/ap06-repo/src/explore/test')
from test_metric_public_cooldown import frozen
n,inputs,policy=frozen('ap06_b65_selection_exact',elapsed_s=31.)
selected=n._metric_select(inputs,policy,.3)[0]
m={'arrival_check':{'goal':[selected.x,selected.y,selected.yaw]}}
