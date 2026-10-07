"""Back up and update the existing MO2 entries, preserving user configuration."""
import json,hashlib,re,shutil,subprocess,sys
from datetime import datetime
from pathlib import Path
from catalog import ROOT,catalog,PLUGIN

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    running=subprocess.run(['powershell','-NoProfile','-Command','Get-Process SkyrimSE,skse64_loader -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName'],capture_output=True,text=True).stdout.strip()
    if running:raise SystemExit('Close Skyrim before installing: '+running)
    games=Path('C:/Users/linos/Desktop/games/+skyrim');mods=games/'MO2/mods'
    blood=mods/'玩法改进-神血-The Stones of Divines-🟩🟨-打怪掉落'
    workshop=mods/'玩法改进-装备工坊-EquipmentWorkshop-Shift+A'
    spid=mods/'功能模组-物品分发-SPID+CID配置-🟪🟨/-important_DISTR.ini'
    release=ROOT.parent/'workshop/packaging/release/EquipmentWorkshop-2.4.1'
    assert blood.is_dir() and workshop.is_dir() and spid.is_file() and (release/'SKSE/Plugins/EquipmentWorkshop.dll').is_file()
    original=spid.read_bytes();editorids={row['editorID'] for row in json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))}
    retained=[];removed=[]
    for line in original.splitlines(keepends=True):
        match=re.match(rb'\s*Item\s*=\s*([^|\s]+)\s*\|',line)
        if match and match.group(1).decode('ascii') in editorids:removed.append(line)
        else:retained.append(line)
    if len(removed)!=16 and not (len(removed)==0 and (blood/'DivineBlood_DISTR.ini').is_file()):
        raise RuntimeError(f'Expected exactly 16 legacy blood rules, found {len(removed)}; mixed SPID file not modified')
    backup=games/'mod-backups'/('DivineBlood-1.0.0-Workshop-2.4.1-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True);shutil.copytree(blood,backup/'divine-blood');shutil.copytree(workshop,backup/'workshop');shutil.copy2(spid,backup/spid.name)
    installed=[]
    def copy_tree(source,destination):
        for f in source.rglob('*'):
            if not f.is_file() or f.name=='meta.ini':continue
            target=destination/f.relative_to(source)
            if target.exists() and (target.suffix=='.ini' or target.name.endswith('.rules.json') or target.name=='EquipmentWorkshop.recycling.json'):continue
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
            assert hashlib.sha256(f.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest()
            installed.append(str(target))
    copy_tree(ROOT/'data',blood);copy_tree(release,workshop)
    # Commit distribution migration last, after the replacement rule file is installed.
    spid.write_bytes(b''.join(retained));assert spid.read_bytes()==b''.join(retained)
    for path,version in ((blood,'1.0.0'),(workshop,'2.4.1')):
        p=path/'meta.ini';text=p.read_text(encoding='utf-8-sig') if p.exists() else '[General]\n'
        text=re.sub(r'(?m)^version=.*$',lambda _: 'version='+version,text)
        if not re.search(r'(?m)^version=',text):text+='\nversion='+version+'\n'
        p.write_text(text,encoding='utf-8')
    report=dict(backup=str(backup),blood=str(blood),workshop=str(workshop),spid=str(spid),removedLegacyRules=len(removed),installed=installed)
    (ROOT/'build/installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'build'/('installation-'+backup.name+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='installed'},ensure_ascii=False))
if __name__=='__main__':main()
