"""Extract the original shield attachment/collision graph without modifying the game."""
from pathlib import Path
from bsa_reference import entries, extract
ROOT=Path(__file__).resolve().parents[1]
game=Path('C:/Users/linos/Desktop/games/+skyrim/SkyrimSE/Data')
model='meshes/armor/elven/elvenshield.nif'
archive=next(p for p in game.glob('Skyrim - Meshes*.bsa') if model in entries(p))
out=ROOT/'build/shield-reference-elvenshield.nif'
out.parent.mkdir(exist_ok=True)
out.write_bytes(extract(archive,model))
print(out)
