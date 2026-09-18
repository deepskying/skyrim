"""Build staff DLL + Papyrus bridge and run native rules tests."""
from pathlib import Path
import subprocess,shutil
ROOT=Path(__file__).resolve().parents[1]
for cmd in (['xmake','f','-m','release','-y'],['xmake','-y'],['xmake','build','-y','staff-rules-test'],['xmake','run','staff-rules-test']):
    subprocess.run(cmd,cwd=ROOT/'native',check=True)
out=ROOT/'data/SKSE/Plugins';out.mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/'native/build/windows/x64/release/ArcaneStaves.dll',out/'ArcaneStaves.dll')
game=Path('C:/Users/linos/Desktop/games/+skyrim');ck=game/'TOOLS/+creation kit'
includes=';'.join(str(p) for p in (ROOT/'source/papyrus',game/'SkyrimSE/Data/Scripts/Source',ck/'Data/Source/Scripts'))
for name in ('AAStaffRuntime','AAStaffRedHit'):
    p=subprocess.run([str(ck/'Papyrus Compiler/PapyrusCompiler.exe'),name,'-i='+includes,'-o='+str(ROOT/'data/scripts'),'-f='+str(ck/'Data/Source/Scripts/TESV_Papyrus_Flags.flg')],capture_output=True,text=True)
    print(p.stdout);(ROOT/'build'/(name+'-compile.log')).write_text(p.stdout+p.stderr,encoding='utf-8');p.check_returncode()
    assert (ROOT/'data/scripts'/(name+'.pex')).read_bytes()[:4]==bytes.fromhex('fa57c0de')
