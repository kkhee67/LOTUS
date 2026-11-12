"""Detect generated contract drift without requiring staged or committed files."""
import subprocess
import sys
from pathlib import Path

FILES = ['contracts/openapi.json', 'contracts/models.schema.json', 'contracts/FIELDS.md']
before = {name: Path(name).read_bytes() for name in FILES}
for module in ('scripts.export_openapi', 'scripts.export_contracts'):
    subprocess.run([sys.executable, '-m', module], check=True)
changed = [name for name in FILES if Path(name).read_bytes() != before[name]]
if changed:
    raise SystemExit('Generated contract drift: ' + ', '.join(changed))
print('Generated Python contracts are current.')
