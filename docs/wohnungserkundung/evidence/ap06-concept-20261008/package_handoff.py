#!/usr/bin/env python3
"""Package the committed candidate and closed synthetic evidence after all runs."""
import hashlib, json, subprocess, tarfile
from datetime import datetime, timezone
from pathlib import Path

REPO=Path('/workspace/Roboter_ws-ap06')
EVIDENCE=REPO/'docs/wohnungserkundung/evidence/ap06-concept-20261008'
OUTPUT=Path('/workspace/artifacts/ap06-konzept-20261008')
CANDIDATE='c5d2a9c00d146851799a907ba725ef0d0f30c815'
BRANCH='feature/ap06-closed-product-validation'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def git(*args):
    return subprocess.check_output(['git','-C',str(REPO),*args],text=True).strip()

def runtime_sha(remote):
    assert remote.startswith('/evidence/')
    try:
        return sha(Path('/workspace/scratch')/remote.removeprefix('/evidence/'))
    except PermissionError:
        # Read only the already bound synthetic install artifact; do not chmod.
        return subprocess.check_output(['docker','exec','ap03-nav2',
            'sha256sum','--',remote],text=True).split()[0]

assert not git('status','--porcelain','--untracked-files=all','--','src','tools','.github/workflows/hwt601-we.yml'), 'Product tree is dirty'
assert not git('diff',CANDIDATE,'HEAD','--','src','tools','.github/workflows/hwt601-we.yml'), 'Product changed after tested candidate'
head=git('rev-parse','HEAD')
assert git('rev-parse','refs/heads/'+BRANCH)==head
OUTPUT.mkdir(parents=True,exist_ok=False)
bundle=OUTPUT/'roboter-ap06-konzept.bundle'
subprocess.run(['git','-C',str(REPO),'bundle','create',str(bundle),'refs/heads/'+BRANCH],check=True)
verified=subprocess.run(['git','-C',str(REPO),'bundle','verify',str(bundle)],capture_output=True,text=True,check=True)
(OUTPUT/'bundle-verify.txt').write_text(verified.stdout+verified.stderr)
# A fresh clone verifies the actual transport, not only the original worktree.
clone=Path('/workspace/scratch/ap06-bundle-transfer-check')
subprocess.run(['git','clone','--quiet','--branch',BRANCH,str(bundle),str(clone)],check=True)
assert subprocess.check_output(['git','-C',str(clone),'rev-parse','HEAD'],text=True).strip()==head
identity=json.loads((EVIDENCE/'stationary-release/joined-source-identity.json').read_text())
assert identity['candidate']==CANDIDATE
for relative, entry in identity['files'].items():
    assert sha(clone/relative)==entry['sha256'], relative
    assert sha(Path('/workspace/scratch/ap06-repo')/relative)==entry['sha256'], relative
native=json.loads((EVIDENCE/'stationary-release/joined-native-identity.json').read_text())
runtime_entries=(native['source_installed_equal']+native['native_binaries']+
    identity['native_plugins']+[identity['additional_native_arithmetic']])
for entry in runtime_entries:
    remote=entry.get('installed',entry.get('path'))
    assert runtime_sha(remote)==entry['sha256'], remote
# The raw evidence archive remains outside Git. It includes the small reports
# too, so a reviewer can extract all closed runs to a separate local directory.
archive=OUTPUT/'ap06-synthetische-belege.tar'
raw=json.loads((EVIDENCE/'local-raw-traces.json').read_text())
with tarfile.open(archive,'w') as tf:
    tf.add(EVIDENCE,arcname=EVIDENCE.name,recursive=True)
    for item in raw:
        path=Path(item['path'])
        assert sha(path)==item['compressed_sha256']
        relative=path.relative_to('/workspace/scratch/ap06-concept-20261008')
        tf.add(path,arcname=str(Path(EVIDENCE.name)/relative),recursive=False)
    for item in json.loads((EVIDENCE/'local-diagnostic-captures.json').read_text()):
        path=Path(item['path'])
        assert sha(path)==item['sha256']
        tf.add(path,arcname=str(Path(EVIDENCE.name)/item['relative']),recursive=False)
manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),
    tested_product_candidate=CANDIDATE,bundle_head=head,branch=BRANCH,
    bundle_verified=True,fresh_clone_verified=True,source_files_verified=len(identity['files']),
    execution_source_files_verified=len(identity['files']),
    installed_and_native_files_verified=len(runtime_entries),
    original_positive_qualification='0/3',hardware_qualified=False,
    handoff_document='docs/wohnungserkundung/JETSON_KONZEPTTEST_AP06.md',
    evidence_report='docs/wohnungserkundung/evidence/ap06-concept-20261008/README.md',
    files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in (bundle,archive,OUTPUT/'bundle-verify.txt')})
(OUTPUT/'uebergabe.json').write_text(json.dumps(manifest,indent=2)+'\n')
(OUTPUT/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n'
    for p in (bundle,archive,OUTPUT/'bundle-verify.txt',OUTPUT/'uebergabe.json')))
print(json.dumps(manifest,indent=2))
