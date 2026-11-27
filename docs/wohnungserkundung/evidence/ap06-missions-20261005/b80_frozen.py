"""Original B76 selection32 inputs; no private/try/health changes."""
from pathlib import Path
import b73_selection_probe as source
source.root=Path('/evidence/ap06-missions-20261005/mission-b-v76-capture')
n,inputs,policy=source.frozen(32)
