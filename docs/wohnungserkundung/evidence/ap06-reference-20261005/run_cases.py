import json,time,subprocess
from pathlib import Path
p=Path('/workspace/scratch/ap06-reference-20261005')
records=json.load(open(p/'commands.json'))
for label,case,domain in [('reference-a','door68_start_a',191),('reference-b','door68_start_b',192),('reference-cancel','cancel',194),('reference-gyro-hold','gyro_hold',195)]:
 command=['docker','exec','ap03-nav2','bash','-c',f'source /opt/ros/humble/setup.bash && source /evidence/ap03-nav2-install/setup.bash && source /evidence/ap06-support-install/setup.bash && source /evidence/ap06-product-install/setup.bash && export AP06_SIMULATION=1 ROS_DOMAIN_ID={domain} OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 && python3 /evidence/ap06-repo/tools/simulation/ap06_closed_product.py --repo /evidence/ap06-repo --tf-probe /evidence/ap06-tf-probe-build/tf_ownership_probe --case {case} --output /evidence/ap06-reference-20261005/{label} --save-partial']
 started=time.time()
 with open(p/(label+'.log'),'w') as out: r=subprocess.run(command,stdout=out,stderr=subprocess.STDOUT)
 records.append(dict(label=label,software_commit='3f66d73',command=command,exit_code=r.returncode,started=started,finished=time.time()))
 (p/'commands.json').write_text(json.dumps(records,indent=2))
 result=p/label/'result.json'
 v=json.load(open(result)) if result.exists() else {}
 print(json.dumps(dict(label=label,exit_code=r.returncode,passed=v.get('passed'),error=v.get('error'),travel_m=v.get('travel_m'),arrivals=v.get('metric',{}).get('arrivals'),observations=v.get('metric',{}).get('observations'))),flush=True)
