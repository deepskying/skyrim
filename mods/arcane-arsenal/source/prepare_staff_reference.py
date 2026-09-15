"""Extract only local vanilla staff reference meshes, never ship their geometry."""
from pathlib import Path
from bsa_reference import entries, extract

ROOT = Path(__file__).resolve().parents[1]
GAME = Path('C:/Users/linos/Desktop/games/+skyrim/SkyrimSE/Data')
DEST = ROOT / 'build/staves-reference'
DEST.mkdir(parents=True, exist_ok=True)
for archive in GAME.glob('Skyrim - Meshes*.bsa'):
    names = entries(archive)
    for name in ('staff01.nif', '1stpersonstaff01.nif'):
        key = 'meshes/weapons/staff01/' + name
        if key in names:
            path = DEST / name
            path.write_bytes(extract(archive, key))
            print(path)
    key='meshes/weapons/iron/waraxe.nif'
    if key in names:
        (DEST/'collision-template.nif').write_bytes(extract(archive,key))
