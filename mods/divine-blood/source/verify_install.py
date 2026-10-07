"""Verify the installed payload and preservation of unrelated mixed SPID lines."""
from pathlib import Path
import json,re,sys
from catalog import ROOT
def main():
    report=json.loads((ROOT/'build/installation.json').read_text(encoding='utf-8'))
    blood=Path(report['blood']);workshop=Path(report['workshop'])
    backup=Path(sys.argv[1]) if len(sys.argv)>1 else Path(report['backup'])
    ids={r['editorID'] for r in json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))}
    original=(backup/'-important_DISTR.ini').read_bytes();retained=[]
    for line in original.splitlines(keepends=True):
        match=re.match(rb'\s*Item\s*=\s*([^|\s]+)\s*\|',line)
        if not match or match.group(1).decode('ascii') not in ids:retained.append(line)
    assert Path(report['spid']).read_bytes()==b''.join(retained)
    for source in (ROOT/'data').rglob('*'):
        if source.is_file() and source.suffix!='.ini':assert source.read_bytes()==(blood/source.relative_to(ROOT/'data')).read_bytes()
    dist=ROOT.parent/'durability-manager/web/dist'
    for view in ('PrismaUI/views/DurabilityManager','MeridianUI/equipmentworkshop'):
        for source in dist.rglob('*'):
            if source.is_file():assert source.read_bytes()==(workshop/view/source.relative_to(dist)).read_bytes()
    assert (workshop/'SKSE/Plugins/EquipmentWorkshop.dll').read_bytes()==(ROOT.parent/'workshop/native/build/windows/x64/release/EquipmentWorkshop.dll').read_bytes()
    if report.get('legacy'):
        assert blood==workshop and not Path(report['legacy']).exists()
        archived=Path(report['archived']) if report.get('archived') else None
        if archived:
            assert archived.is_dir()
            for name in ('SKSE/Plugins/DivineBlood.ini','DivineBlood_DISTR.ini'):
                if (archived/name).exists():assert (workshop/name).read_bytes()==(archived/name).read_bytes()
        for name in report.get('profiles',[]):
            profile=Path(name);raw=profile.read_bytes();old=Path(report['legacy']).name.encode('utf-8')
            assert all(line.strip() not in (b'+'+old,b'-'+old) for line in raw.splitlines())
            assert (b'+'+workshop.name.encode('utf-8')) in raw.splitlines()
            for filename in ('plugins.txt','loadorder.txt'):
                saved=Path(report['backup'])/'profiles'/profile.parent.name/filename
                if saved.exists():assert saved.read_bytes()==(profile.parent/filename).read_bytes()
            # The retained ESP must have exactly one enabled provider.
            mods=workshop.parent
            providers=[mods/line[1:].decode('utf-8') for line in raw.splitlines() if line.startswith(b'+') and (mods/line[1:].decode('utf-8')/'The Blood of Divines.esp').is_file()]
            assert providers==[workshop],providers
    print('Installed payload, retained configs, sole ESP provider and unchanged plugin order/SPID rules verified')
if __name__=='__main__':main()
