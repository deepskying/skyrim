"""Verify, package and install the prototype into the selected MO2 profile.

Existing files/profile lists are backed up. No game root or other mod is edited.
"""
import json,hashlib,shutil,subprocess,zipfile,datetime
from paths import *

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
subprocess.run([sys.executable,str(ROOT/'source/verify_release.py')],check=True,capture_output=True)
check=subprocess.run(['powershell','-NoProfile','-Command',"Get-Process SkyrimSE,ModOrganizer -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName"],capture_output=True,text=True)
running=check.stdout.strip().splitlines()
if 'SkyrimSE' in running:raise SystemExit('Game is running; build is ready. Install after exiting Skyrim.')
mo2_running='ModOrganizer' in running
mo2=MODS.parent
ini=(mo2/'ModOrganizer.ini').read_text(encoding='utf-8-sig')
assert 'selected_profile=@ByteArray(-std-)' in ini
profile=mo2/'profiles/-std-'
mod_name='武器魔法-魔法箭工坊-Magic Arrows'
dest=MODS/mod_name
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
backup=GAME.parent/'mod-backups'/('MagicArrows-'+stamp)
backup.mkdir(parents=True,exist_ok=False)
for name in ('modlist.txt','plugins.txt','loadorder.txt'):
    path=profile/name
    if path.exists():shutil.copy2(path,backup/name)
if dest.exists():shutil.copytree(dest,backup/'previous-mod')
binary=ROOT/'native/build/windows/x64/release/MagicArrows.dll'
assert binary.is_file(), 'Build native DLL first'
(DATA/'SKSE/Plugins').mkdir(parents=True,exist_ok=True)
shutil.copy2(binary,DATA/'SKSE/Plugins/MagicArrows.dll')
web=DATA/'PrismaUI/views/MagicArrows';web.mkdir(parents=True,exist_ok=True)
for name in ('index.html','style.css','app.js'):shutil.copy2(ROOT/'web'/name,web/name)
meta='[General]\ngameName=Skyrim Special Edition\nmodid=0\nversion=0.9.8\ncategory=0\nnotes=Draggable per-save player ammo queue with ordered depletion switching.\n'
(DATA/'meta.ini').write_text(meta,encoding='utf-8')
shutil.copy2(ROOT/'README.md',DATA/'README.md')
(DATA/'docs').mkdir(exist_ok=True)
shutil.copy2(ROOT/'docs/marc-compatibility.md',DATA/'docs/marc-compatibility.md')
shutil.copy2(ROOT/'docs/arrow-identity.md',DATA/'docs/arrow-identity.md')
shutil.copy2(ROOT/'docs/ammo-queue.md',DATA/'docs/ammo-queue.md')
release=ROOT/'release';release.mkdir(exist_ok=True)
archive=release/'MagicArrows-0.9.8-MO2.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for path in sorted(DATA.rglob('*')):
        if path.is_file():z.write(path,path.relative_to(DATA).as_posix())
config=dest/'SKSE/Plugins/MagicArrows.ini'
saved_config=config.read_bytes() if config.exists() else None
shutil.copytree(DATA,dest,dirs_exist_ok=True)
if saved_config is not None:config.write_bytes(saved_config)

def update_list(name,value,top=False):
    path=profile/name
    old=path.read_bytes() if path.exists() else b''
    bom=b'\xef\xbb\xbf' if old.startswith(b'\xef\xbb\xbf') else b''
    txt=old[len(bom):].decode('utf-8');newline='\r\n' if '\r\n' in txt else '\n'
    lines=txt.splitlines();identity=value.lstrip('+-*')
    matches=[i for i,line in enumerate(lines) if line.lstrip('+-*')==identity]
    assert len(matches)<=1
    if matches:lines[matches[0]]=value
    elif top:lines.insert(1 if lines and lines[0].startswith('#') else 0,value)
    else:lines.append(value)
    data=bom+(newline.join(lines)+newline).encode('utf-8')
    path.write_bytes(data)
    old_other=[line for line in txt.splitlines() if line.lstrip('+-*')!=identity]
    new_other=[line for line in lines if line.lstrip('+-*')!=identity]
    assert old_other==new_other

# A running MO2 owns the in-memory profile. Install files now and let the user
# refresh/enable the new mod instead of racing its next profile write.
if not mo2_running:
    update_list('modlist.txt','+'+mod_name,True)
    update_list('plugins.txt','*MagicArrows.esp')
    update_list('loadorder.txt','MagicArrows.esp')
files=[]
for p in DATA.rglob('*'):
    if p.is_file():
        target=dest/p.relative_to(DATA)
        if target!=config or saved_config is None:assert sha(p)==sha(target)
        files.append(dict(path=p.relative_to(DATA).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==sorted(f['path'] for f in files)
    for f in files:assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256']
enabled=('+'+mod_name) in (profile/'modlist.txt').read_text(encoding='utf-8-sig').splitlines() and '*MagicArrows.esp' in (profile/'plugins.txt').read_text(encoding='utf-8-sig').splitlines()
report=dict(version='0.9.8',visual_revision='ordered-ammo-queue',installed=str(dest),profile=str(profile),profile_enabled=enabled,activation='Enabled in profile' if enabled else 'Refresh MO2 and enable mod/plugin',backup=str(backup),archive=str(archive),archive_sha256=sha(archive),config_preserved=saved_config is not None,files=files,game_tested=False)
(BUILD/'installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=True,indent=2))
