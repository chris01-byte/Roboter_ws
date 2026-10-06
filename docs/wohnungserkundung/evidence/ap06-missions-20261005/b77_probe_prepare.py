from pathlib import Path
b=Path('/workspace/scratch/ap06-missions-20261005')
s=(b/'b73_native_local_probe.py').read_text().replace('b73-native-local-probe','b77-native-local-probe')
s=s.replace("# Recorded actual first arrival remains inputs[2].","# Original coherent B73 selection14 snapshot; native readonly query only.")
s=s.replace("# keep all measured alternatives","# keep all measured alternatives")
(b/'b77_native_local_probe.py').write_text(s)
