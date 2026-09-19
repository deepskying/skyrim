"""Small tiled dark metal/leather textures, with complete DDS mip chains."""
from pathlib import Path
import subprocess, random, math, struct
ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'art/shields';ART.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'data/textures/armor/arcanearsenal';OUT.mkdir(parents=True,exist_ok=True)
CONV=Path('C:/Users/linos/Desktop/games/+skyrim/TOOLS/+tools-VRAMr/VRAMr/tools/texconv.exe')
rng=random.Random(530)
for name,base in [('metal',(51,45,41)),('grip',(40,26,21))]:
    pixels=bytearray()
    for y in range(512):
        for x in range(512):
            grain=rng.gauss(0,2.5)+2*math.sin(x*.27)+1.5*math.sin(y*.18)
            pixels.extend(max(0,min(255,round(v+grain))) for v in reversed(base))
    src=ART/('shield_'+name+'_d.tga')
    src.write_bytes(struct.pack('<BBBHHBHHHHBB',0,0,2,0,0,0,0,0,512,512,24,32)+pixels)
    subprocess.run([str(CONV),'-nologo','-y','-f','BC3_UNORM','-m','0','-o',str(OUT),str(src)],check=True,capture_output=True)
print('Shield trim textures built')
