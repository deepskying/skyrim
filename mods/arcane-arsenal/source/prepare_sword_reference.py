"""Extract the user's vanilla IronSword mesh using the normal Python runtime."""
from pathlib import Path
from bsa_reference import extract, entries
ROOT=Path(__file__).resolve().parents[1]
game=Path('C:/Users/linos/Desktop/games/+skyrim/SkyrimSE/Data')
model='meshes/weapons/iron/longsword.nif'
archive=next(p for p in game.glob('Skyrim - Meshes*.bsa') if model in entries(p))
destination=ROOT/'build/ironsword-reference.nif'
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_bytes(extract(archive,model))
print(destination)
