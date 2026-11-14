"""Bind final AP06 source/install without rewriting original scenario/plugin pins."""
from pathlib import Path
import hashlib,json,subprocess
root=Path('/workspace/Roboter_ws-ap06')
e=Path('/workspace/scratch/ap06-missions-20261005')
copy=Path('/workspace/scratch/ap06-repo')
def host(p):return Path(str(p).replace('/evidence/','/workspace/scratch/',1))
def contents(p):
    try:return p.read_bytes()
    except PermissionError:
        return subprocess.check_output(['docker','exec','ap03-nav2','cat',str(p).replace('/workspace/scratch/','/evidence/',1)])
def sha(p):return hashlib.sha256(contents(p)).hexdigest()
code=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD']).decode().strip()
s=json.loads((e/'source-identity-v25.json').read_text())
s['candidate']=code
s['qualification']='v46 build/tests/native verified; C248 negative, Cancel249/Gyro250 passed; original 3/3 not established; A/B start coverage blocked'
for relative in ('src/explore/test/test_metric_near_start_priority.py','src/explore/test/data/ap06_a227_start_selection.json','src/explore/test/data/ap06_a227_start_selection.npz','src/explore/test/test_metric_native_clipping.py','src/explore/test/test_metric_native_distances.py','src/explore/explore/_reserved_sweep.c','src/explore/test/test_metric_native_sweep.py',
                 'src/explore/test/test_metric_task_view_group.py',
                 'src/explore/test/data/ap06_b102_terminal_public_task.json',
                 'src/explore/test/data/ap06_b102_terminal_public_task.npz',
                 '.github/workflows/hwt601-we.yml','src/explore/explore/action_client.py',
                 'src/explore/test/test_action_client_registration.py',
                 'src/explore/test/test_metric_actual_stop.py',
                 'src/explore/test/data/ap06_c119_terminal_native_stop.json',
                 'src/explore/test/data/ap06_c119_terminal_native_stop.npz','src/explore/test/conftest.py',
                 'src/explore/test/test_metric_native_continuation.py',
                 'src/explore/test/data/ap06_b126_native_continuation.json',
                 'src/explore/test/data/ap06_b126_native_continuation.npz',
                 'src/explore/test/test_metric_local_remainder.py',
                 'src/explore/test/data/ap06_b147_local_remainder.json',
                 'src/explore/test/data/ap06_b147_local_remainder.npz',
                 'src/explore/test/test_metric_recorded_raster.py',
                 'src/explore/test/data/ap06_b166_recorded_raster.json',
                 'src/explore/test/data/ap06_b166_recorded_raster.npz',
                 'src/explore/test/test_metric_start_raster.py',
                 'src/explore/test/data/ap06_b176_start_raster.json',
                 'src/explore/test/data/ap06_b176_start_raster.npz',
                 'src/explore/test/test_metric_egress_region.py',
                 'src/explore/test/test_metric_egress_batch.py',
                 'src/explore/test/test_metric_fresh_motion.py',
                 'src/explore/test/test_metric_selection_arithmetic.py',
                 'src/explore/test/test_metric_selection_components.py',
                 'src/explore/test/test_metric_pending_scan.py',
                 'src/explore/test/data/ap06_b216_pending_scan.json',
                 'src/explore/test/data/ap06_b216_pending_scan.npz',
                 'src/explore/test/data/ap06_b207_terminal_selection.json',
                 'src/explore/test/data/ap06_b207_terminal_selection.npz',
                 'src/explore/test/data/ap06_b201_selection_trajectory.json',
                 'src/explore/test/data/ap06_b201_selection_trajectory.npz',
                 'src/explore/test/data/ap06_b186_decision_inputs.json',
                 'src/explore/test/data/ap06_b186_decision_inputs.npz'):
    s['files'][relative]={}
helper='src/explore/explore/action_client.py'
helper_install='/evidence/ap06-old-product-install/explore/lib/python3.10/site-packages/explore/action_client.py'
s['files'][helper]['installed']=helper_install
for relative,entry in s['files'].items():
    assert (root/relative).read_bytes()==(copy/relative).read_bytes(),relative
    entry.update(sha256=sha(root/relative),source_execution_equal=True)
    if entry.get('installed'):
        assert (root/relative).read_bytes()==contents(host(entry['installed'])),relative
        entry['source_execution_installed_equal']=True
for plugin in s['native_plugins']:
    assert sha(host(plugin['path']))==plugin['sha256'],plugin['path']
s['masterplan_sha256']=sha(root/'docs/wohnungserkundung/MASTERPLAN.md')
s['manifest_sha256']=sha(root/'tools/simulation/ap06_product_scenarios.json')
assert s['masterplan_sha256']=='030782dc0cce24d23ef730783703f91cac6957ceb4b7305a224342fba74a8a10'
assert s['manifest_sha256']=='54132aaaca7ccee8412d5a5078410f49cb2f388da08c8f18899e5493ab4021da'
kernels=list(host('/evidence/ap06-old-product-install/explore/lib/python3.10/site-packages/explore').glob('_reserved_sweep*.so'))
assert len(kernels)==1
kernel=dict(package='explore',path=str(kernels[0]).replace('/workspace/scratch/','/evidence/',1),
            sha256=sha(kernels[0]),source='src/explore/explore/_reserved_sweep.c',
            source_sha256=sha(root/'src/explore/explore/_reserved_sweep.c'),
            compile_flags=['-O3','-fno-fast-math','-ffp-contract=off'],authority='pure arithmetic only')
s['additional_native_arithmetic']=kernel
(e/'source-identity-v46.json').write_text(json.dumps(s,indent=2)+'\n')
n=json.loads((e/'native-identity-v25-bound.json').read_text())
n['candidate']=code;n['qualification']=s['qualification']
n['source_installed_equal'].append(dict(source=helper,installed=helper_install))
for entry in n['source_installed_equal']:
    assert (copy/entry['source']).read_bytes()==contents(host(entry['installed'])),entry['source']
    entry['sha256']=sha(copy/entry['source'])
for entry in n['native_binaries']:
    assert sha(host(entry['path']))==entry['sha256'],entry['path']
n['native_binaries'].append(kernel)
(e/'native-identity-v46-bound.json').write_text(json.dumps(n,indent=2)+'\n')
print(json.dumps(dict(candidate=code,source_files=len(s['files']),installed_files=len(n['source_installed_equal']),
                     native_binaries=len(n['native_binaries']),manifest=s['manifest_sha256'],master=s['masterplan_sha256'],kernel=kernel['sha256'])),flush=True)
