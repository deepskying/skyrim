from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
GAME=Path(r'C:\Users\linos\Desktop\games\+skyrim\SkyrimSE')
MODS=GAME.parent/'MO2/mods'
ADDON=REPO/'reference/bow-tools/blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly'
sys.path.insert(0,str(ADDON))
BUILD=ROOT/'build'
DATA=ROOT/'data'
MESH=DATA/'meshes/magicarrows'
TEX=DATA/'textures/magicarrows'
for p in (BUILD,DATA,MESH,TEX,ROOT/'art'):p.mkdir(parents=True,exist_ok=True)
SPECS=[
    dict(key='blood',name='嗜血箭',color=(1,.025,.06),core=(1,.18,.22),particle='drop',id=0x800),
    dict(key='holy',name='圣辉箭',color=(1,.62,.12),core=(1,.88,.45),particle='spark',id=0x810),
    dict(key='soul',name='星魂箭',color=(.36,.14,1),core=(.88,.80,1),particle='star',id=0x820),
]
