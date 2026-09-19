"""Select integrated runtime files, excluding experiments from concurrent tasks."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def runtime_paths():
    root=ROOT/'data'
    catalog=json.loads((ROOT/'source/catalog.json').read_text('utf-8'))
    paths=[root/'ArcaneArsenal.esp',root/'seq/ArcaneArsenal.seq',root/'scripts/AARedDrawFX.pex']
    paths += [root/'meshes/weapons/arcanearsenal'/(s['key']+'.nif') for s in catalog]
    paths += sorted((root/'textures/weapons/arcanearsenal').glob('*.dds'))
    assert all(p.is_file() for p in paths)
    assert len(set(paths))==len(paths)
    return sorted(paths)
