"""Rename this MO2 mod and preserve each profile's activation and priority.

MO2 must release its cached mod lists first. Uses a normal window-close request,
never kills the process; stops if it remains open. No plugin lists are edited.
"""
from pathlib import Path
import subprocess,datetime,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
MO2=Path(r'C:\Users\linos\Desktop\games\+skyrim\MO2')
OLD='Arcane Arsenal - Bow Collection';NEW='幻律兵装 - Arcane Armory'
source=MO2/'mods'/OLD;dest=MO2/'mods'/NEW
assert source.resolve().parent==(MO2/'mods').resolve() and dest.resolve().parent==(MO2/'mods').resolve()
if not source.exists() and dest.is_dir():
    print('Mod already renamed');raise SystemExit(0)
assert source.is_dir() and (source/'ArcaneArsenal.esp').is_file() and not dest.exists()
command='''if (Get-Process SkyrimSE -ErrorAction SilentlyContinue) { exit 2 }
$modApp = Get-Process ModOrganizer -ErrorAction SilentlyContinue
foreach ($modProcess in $modApp) {
    if ($modProcess.Path -ne 'C:\\Users\\linos\\Desktop\\games\\+skyrim\\MO2\\ModOrganizer.exe') { exit 3 }
    if (-not $modProcess.CloseMainWindow()) { exit 4 }
    if (-not $modProcess.WaitForExit(8000)) { exit 5 }
}'''
result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert result.returncode==0,f'Close Skyrim/MO2 before renaming; graceful-close result {result.returncode}'
backup=ROOT/'build'/('mo2-rename-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir()
updates=[]
pattern=re.compile(rb'(?m)^([+-])'+re.escape(OLD.encode())+rb'(?=\r?$)')
for p in (MO2/'profiles').glob('*/modlist.txt'):
    original=p.read_bytes()
    modified,count=pattern.subn(lambda m:m.group(1)+NEW.encode('utf-8'),original)
    if count:
        assert count==1
        saved=backup/p.parent.name/p.name;saved.parent.mkdir();shutil.copy2(p,saved)
        updates.append((p,original,modified))
assert updates,'No matching profile entry; inspect MO2 configuration'
renamed=False;written=[]
try:
    source.rename(dest);renamed=True
    for p,original,modified in updates:
        assert p.read_bytes()==original,'Profile changed concurrently'
        p.write_bytes(modified);written.append((p,original))
    assert dest.is_dir() and not source.exists()
    for p,original,modified in updates:assert p.read_bytes()==modified
except Exception:
    for p,original in written:p.write_bytes(original)
    if renamed:dest.rename(source)
    raise
report={'old_name':OLD,'new_name':NEW,'profiles':[str(p) for p,a,b in updates],'backup':str(backup),'activation_and_line_order_preserved':True,'verified':True}
(ROOT/'build/rename-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
