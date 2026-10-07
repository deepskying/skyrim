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
    print('Installed payload hashes and byte-preserved unrelated SPID rules verified')
if __name__=='__main__':main()
