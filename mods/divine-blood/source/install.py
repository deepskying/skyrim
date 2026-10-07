"""Install the unified workshop, preserving settings and archiving the retired blood entry."""
import json,hashlib,re,shutil,subprocess,sys
from datetime import datetime
from pathlib import Path
from catalog import ROOT,PLUGIN

VERSION='2.4.7'

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    running=subprocess.run(['powershell','-NoProfile','-Command','Get-Process SkyrimSE,skse64_loader -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName'],capture_output=True,text=True).stdout.strip()
    if running:raise SystemExit('Close Skyrim before installing: '+running)
    games=Path('C:/Users/linos/Desktop/games/+skyrim');mo2=games/'MO2';mods=mo2/'mods'
    legacy=mods/'玩法改进-神血-The Stones of Divines-🟩🟨-打怪掉落'
    workshop=mods/'玩法改进-装备工坊-EquipmentWorkshop-Shift+A'
    spid=mods/'功能模组-物品分发-SPID+CID配置-🟪🟨/-important_DISTR.ini'
    release=ROOT.parent/f'workshop/packaging/release/EquipmentWorkshop-{VERSION}'
    assert workshop.is_dir() and spid.is_file()
    for name in (PLUGIN,'DivineBlood_DISTR.ini','SKSE/Plugins/DivineBlood.ini','SKSE/Plugins/EquipmentWorkshop.dll'):
        assert (release/name).is_file(),name
    assert len(list((release/'meshes/DivineBlood').glob('*.nif')))==16
    profiles=[]
    for path in sorted((mo2/'profiles').glob('*/modlist.txt')):
        raw=path.read_bytes();lines=raw.splitlines(keepends=True)
        old=legacy.name.encode('utf-8');new=workshop.name.encode('utf-8')
        if any(line.strip() in (b'+'+old,b'-'+old,b'+'+new) for line in lines):
            assert any(line.strip()==b'+'+new for line in lines),'Workshop must be enabled: '+str(path)
            plugins=path.parent/'plugins.txt'
            assert plugins.is_file() and ('*'+PLUGIN).encode() in plugins.read_bytes().splitlines(),'Blood ESP must remain enabled: '+str(plugins)
            retained=[line for line in lines if line.strip() not in (b'+'+old,b'-'+old)]
            profiles.append((path,raw,b''.join(retained)))
    original=spid.read_bytes();editorids={row['editorID'] for row in json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))}
    retained=[];removed=[]
    for line in original.splitlines(keepends=True):
        match=re.match(rb'\s*Item\s*=\s*([^|\s]+)\s*\|',line)
        if match and match.group(1).decode('ascii') in editorids:removed.append(line)
        else:retained.append(line)
    if len(removed) not in (0,16):raise RuntimeError(f'Expected 0 or 16 legacy blood rules, found {len(removed)}')
    backup=games/'mod-backups'/('UnifiedWorkshop-'+VERSION+'-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True);shutil.copytree(workshop,backup/'workshop');shutil.copy2(spid,backup/spid.name)
    for path,raw,updated in profiles:
        dst=backup/'profiles'/path.parent.name;dst.mkdir(parents=True)
        for name in ('modlist.txt','plugins.txt','loadorder.txt'):
            source=path.parent/name
            if source.exists():shutil.copy2(source,dst/name)
    # Move custom blood settings into the workshop before applying package defaults.
    if legacy.exists():
        for name in ('SKSE/Plugins/DivineBlood.ini','DivineBlood_DISTR.ini'):
            src=legacy/name;dst=workshop/name
            if src.exists() and not dst.exists():
                dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    installed=[]
    for source in release.rglob('*'):
        if not source.is_file() or source.name=='meta.ini':continue
        target=workshop/source.relative_to(release)
        if target.exists() and (target.suffix=='.ini' or target.name.endswith('.rules.json') or target.name=='EquipmentWorkshop.recycling.json'):continue
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest()
        installed.append(str(target))
    # Verify every blood resource before retiring its MO2 entry.
    for source in (ROOT/'data').rglob('*'):
        if source.is_file():
            target=workshop/source.relative_to(ROOT/'data');assert target.is_file(),str(target)
            if source.suffix!='.ini':assert source.read_bytes()==target.read_bytes(),str(target)
    spid.write_bytes(b''.join(retained));assert spid.read_bytes()==b''.join(retained)
    for path,raw,updated in profiles:
        assert path.read_bytes()==raw,'MO2 profile changed during migration: '+str(path)
        path.write_bytes(updated)
        for name in ('plugins.txt','loadorder.txt'):
            source=path.parent/name;saved=backup/'profiles'/path.parent.name/name
            if saved.exists():assert source.read_bytes()==saved.read_bytes()
    archived=None
    if legacy.exists():
        # Both absolute paths are checked against the explicitly intended roots.
        assert legacy.resolve().parent==mods.resolve()
        destination=backup/'retired-divine-blood'
        assert destination.resolve().is_relative_to((games/'mod-backups').resolve()) and not destination.exists()
        shutil.move(str(legacy),str(destination));archived=str(destination)
    p=workshop/'meta.ini';text=p.read_text(encoding='utf-8-sig') if p.exists() else '[General]\n'
    text=re.sub(r'(?m)^version=.*$',lambda _: 'version='+VERSION,text)
    if not re.search(r'(?m)^version=',text):text+='\nversion='+VERSION+'\n'
    p.write_text(text,encoding='utf-8')
    report=dict(backup=str(backup),blood=str(workshop),legacy=str(legacy),archived=archived,workshop=str(workshop),spid=str(spid),profiles=[str(p) for p,_,_ in profiles],removedLegacyRules=len(removed),installed=installed)
    (ROOT/'build/installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'build'/('installation-'+backup.name+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='installed'},ensure_ascii=False))
if __name__=='__main__':main()
