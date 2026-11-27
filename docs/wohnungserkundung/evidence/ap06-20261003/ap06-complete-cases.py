import subprocess, pathlib, json
root=pathlib.Path('/workspace/scratch')
results=[]
for index,(case,label) in enumerate([('door68_start_a','complete-a'),('door68_start_b','complete-b'),('door80_start_c','complete-c'),('cancel','complete-cancel'),('gyro_hold','complete-gyro-hold')]):
 print('START',label,flush=True)
 command=['docker','exec','ap03-nav2','bash','-c',f'source /opt/ros/humble/setup.bash && source /evidence/ap03-nav2-install/setup.bash && source /evidence/ap06-support-install/setup.bash && source /evidence/ap06-product-install/setup.bash && export AP06_SIMULATION=1 ROS_DOMAIN_ID={191+index} OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 && python3 /evidence/ap06-repo/tools/simulation/ap06_closed_product.py --repo /evidence/ap06-repo --tf-probe /evidence/ap06-tf-probe-build/tf_ownership_probe --case {case} --output /evidence/ap06-runs/{label} --save-partial']
 with (root/f'ap06-{label}.log').open('w') as f:
  result=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
 results.append(dict(label=label,exit_code=result.returncode,command=command))
 (root/'ap06-complete-case-commands.json').write_text(json.dumps(results,indent=2)+'\n')
 data=json.loads((root/'ap06-runs'/label/'result.json').read_text())
 print('RESULT',label,json.dumps({k:data.get(k) for k in ['passed','error','travel_m','injection_to_standstill_s','hold_to_standstill_s']}),flush=True)
