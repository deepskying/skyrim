"""Extract the local vanilla IronBattleAxe attachment and collision reference."""
from pathlib import Path
from bsa_reference import entries,extract
ROOT=Path(__file__).resolve().parents[1]
model='meshes/weapons/iron/ironbattleaxe.nif'
game=Path('C:/Users/linos/Desktop/games/+skyrim/SkyrimSE/Data')
archive=next(p for p in game.glob('Skyrim - Meshes*.bsa') if model in entries(p))
destination=ROOT/'build/ironbattleaxe-reference.nif'
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_bytes(extract(archive,model))
print(destination)
