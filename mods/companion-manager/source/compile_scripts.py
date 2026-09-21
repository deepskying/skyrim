from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
GAME=Path(r'C:/Users/linos/Desktop/games/+skyrim')
CK=GAME/'TOOLS/+creation kit'
source=ROOT/'source/papyrus';out=ROOT/'data/Scripts'
out.mkdir(parents=True,exist_ok=True)
includes=';'.join(str(p) for p in (source,GAME/'SkyrimSE/Data/Scripts/Source',CK/'Data/Source/Scripts'))
for script in ('CMController','CMDialogue','CMRandomOutfitTopic','CMOutfitPartTopic','CMOutfitSaveTopic'):
    result=subprocess.run([str(CK/'Papyrus Compiler/PapyrusCompiler.exe'),script,'-i='+includes,'-o='+str(out),'-f='+str(CK/'Data/Source/Scripts/TESV_Papyrus_Flags.flg')],capture_output=True,text=True)
    print(result.stdout+result.stderr);result.check_returncode()
    assert (out/(script+'.pex')).read_bytes()[:4]==bytes.fromhex('fa57c0de')
