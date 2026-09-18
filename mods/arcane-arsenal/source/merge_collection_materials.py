"""Merge the verified 140-model material patch into a newer integrated release.

Run only after coordinating the release handoff. Fail before writing if any
target changed since 0.46; new weapons, plugin, scripts and DLLs are untouched.
"""
from pathlib import Path
import json,hashlib,shutil,datetime
ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'build/all-materials-stage'
report=json.loads((STAGE/'verification.json').read_text(encoding='utf-8'))
assert report['verified'] and report['changed']==140
targets=[]
for entry in report['weapons']:
    if not entry['changed']:continue
    rel=Path('meshes/weapons/arcanearsenal')/(entry['key']+'.nif')
    old=(STAGE/'baseline'/rel).read_bytes();new=(STAGE/'data'/rel).read_bytes()
    assert hashlib.sha256(new).hexdigest()==entry['sha256']
    assert (ROOT/'data'/rel).read_bytes()==old, f'Concurrent model change: {rel}'
    targets.append((rel,old,new))
backup=ROOT/'build'/('before-all-materials-merge-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(exist_ok=False)
for rel,old,new in targets:
    p=backup/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(old)
try:
    for rel,old,new in targets:(ROOT/'data'/rel).write_bytes(new)
    for rel,old,new in targets:assert (ROOT/'data'/rel).read_bytes()==new
except Exception:
    for rel,old,new in targets:(ROOT/'data'/rel).write_bytes(old)
    raise
result=dict(changed=len(targets),backup=str(backup),verified=True)
(ROOT/'build/collection-materials-merge.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
