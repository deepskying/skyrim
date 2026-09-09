"""Compile using the installed 2019 Creation Kit and existing SKSE declarations."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:\Users\linos\Desktop\games\+skyrim')
CK=GAME/'TOOLS/+creation kit'
source=ROOT/'source/papyrus'
out=ROOT/'data/scripts';out.mkdir(parents=True,exist_ok=True)
includes=';'.join(str(p) for p in (source,GAME/'SkyrimSE/Data/Scripts/Source',CK/'Data/Source/Scripts'))
result=subprocess.run([str(CK/'Papyrus Compiler/PapyrusCompiler.exe'),'AARedDrawFX',
    '-i='+includes,'-o='+str(out),'-f='+str(CK/'Data/Source/Scripts/TESV_Papyrus_Flags.flg')],
    capture_output=True,text=True)
(ROOT/'build/draw-fx-compile.log').write_text(result.stdout+result.stderr,encoding='utf-8')
print(result.stdout);result.check_returncode()
assert (out/'AARedDrawFX.pex').read_bytes()[:4]==bytes.fromhex('fa57c0de')
