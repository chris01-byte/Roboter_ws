"""Lossless archive of this task's inactive reproducible SLAM build only."""
from pathlib import Path
import hashlib,json,tarfile,shutil,os
base=Path(os.environ.get('AP06_CACHE_ROOT','/workspace/scratch/ap06-missions-20261005'));folder=base/'slam-build';out=base/'b75-inactive-slam-build.tar.gz'
assert folder.exists() and out.exists()
records={str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file() and not p.is_symlink()}
before=shutil.disk_usage(base).free
# Archive already created by original host attempt; verify before root-owned cache removal.
verified=set()
with tarfile.open(out,'r|gz') as archive:
 for member in archive:
  if member.name not in records:continue
  if member.islnk():assert member.linkname in verified and records[member.linkname]==records[member.name]
  else:
   f=archive.extractfile(member);assert f is not None
   h=hashlib.sha256()
   for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
   assert h.hexdigest()==records[member.name],member.name
  verified.add(member.name)
assert verified==set(records)
shutil.rmtree(folder)
record=dict(folder='slam-build',regular_file_sha256=records,archive_bytes=out.stat().st_size,verified=True,free_before=before,free_after=shutil.disk_usage(base).free)
out.with_suffix('.manifest.json').write_text(json.dumps(record,indent=2)+'\n')
print({k:v for k,v in record.items() if k!='regular_file_sha256'})
