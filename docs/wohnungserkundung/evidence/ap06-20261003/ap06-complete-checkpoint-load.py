import json
from pathlib import Path
from explore.exploration_persistence import MapVersionBinding,ExplorationStateRepository
from explore.metric_checkpoint import validate_checkpoint
from robot_map_manager.map_core import MapRepository
rows=[]
for name in ['complete-a','complete-b','complete-c','complete-cancel','complete-gyro-hold']:
 p=Path('/evidence/ap06-runs')/name
 files=list((p/'checkpoints').rglob('state-*.json'))
 if not files:
  rows.append(dict(run=name,map_pair_valid=False,checkpoint=json.loads((p/'result.json').read_text()).get('checkpoint_after_save'),active_resume_tested=False))
  continue
 envelope=json.loads(files[0].read_text())
 binding=MapVersionBinding(**envelope['map_binding'])
 loaded=ExplorationStateRepository(p/'checkpoints').load(binding,validate_state=validate_checkpoint)
 versions=MapRepository(p/'maps').list_versions(name='amadeus')
 matching=[v for v in versions if v.version==binding.version and v.fingerprint==binding.fingerprint]
 assert len(matching)==1
 assert loaded.state['fingerprint']==binding.fingerprint
 assert loaded.state['resume_authorizes_motion'] is False
 rows.append(dict(run=name,sequence=loaded.sequence,map_id=loaded.state['saved_map_id'],outcome=loaded.state['outcome'],map_pair_valid=True,resume_authorizes_motion=False,active_resume_tested=False,arrivals=loaded.state['arrivals'],observations=loaded.state['observations']))
print(json.dumps(rows,indent=2))
