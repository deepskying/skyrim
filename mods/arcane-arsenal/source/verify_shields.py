"""Validate shield equipment records, final native NIFs, physics and upgrade isolation."""
from pathlib import Path
import json,sys,struct,hashlib,math
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'reference/bow-tools/blender-4.5.13-windows-x64/portable/scripts/addons/io_scene_nifly'))
from pyn.pynifly import NifFile
from nif_blocks import NifBlocks
from plugin_records import records,subrecords,edid
from apply_approved_sword_materials import shapes,texture_paths
from shield_records import CATALOG,CHEST_FORM,NEXT_FORM
from release_assets import runtime_paths
U32=lambda b:struct.unpack('<I',b)[0]
items=list(records(ROOT/'data/ArcaneArsenal.esp'));byform={r['form']:r for r in items}
master=Path('C:/Users/linos/Desktop/games/+skyrim/SkyrimSE/Data/Skyrim.esm')
originals=list(records(master,{b'ARMO',b'ARMA'}))
armor=next(r for r in originals if edid(r)=='ArmorElvenShield');armorfields=dict(subrecords(armor['data']))
addon=next(r for r in originals if r['form']==U32(armorfields[b'MODL']))
native_ref=NifBlocks(ROOT/'build/shield-reference-elvenshield.nif')
assert len([r for r in items if r['sig']==b'ARMO'])==len(CATALOG)==4
assert len([r for r in items if r['sig']==b'ARMA'])==4
assert len(byform)==len(items)==531
assert struct.unpack('<fII',dict(subrecords(items[0]['data']))[b'HEDR'])[1:]==(530,NEXT_FORM)
allchest=next(r for r in items if edid(r)=='AAAllBowsTestChest')
chest=byform[CHEST_FORM];contents=[struct.unpack('<II',v) for k,v in subrecords(chest['data']) if k==b'CNTO']
assert U32(dict(subrecords(chest['data']))[b'COCT'])==len(contents)==4
reports=[]
for spec in CATALOG:
    key=spec['key'];ar=byform[0x03000000|int(spec['armor_form'],16)]
    aa=byform[0x03000000|int(spec['addon_form'],16)]
    af=dict(subrecords(ar['data']));ap=list(subrecords(aa['data']));aaf=dict(ap)
    assert edid(ar)=='AA'+key and af[b'FULL'].rstrip(b'\0').decode()==spec['name']
    assert U32(af[b'DNAM'])==9000 and struct.unpack('<If',af[b'DATA'])==(1800,8.)
    assert U32(af[b'MODL'])==aa['form']
    assert af[b'BOD2']==aaf[b'BOD2']==struct.pack('<II',0x200,0)
    assert af[b'ETYP']==armorfields[b'ETYP'] and af[b'KWDA']==armorfields[b'KWDA']
    assert b'EITM' not in af
    assert [(k,v) for k,v in ap if k in (b'MODL',b'RNAM',b'DNAM')]==[(k,v) for k,v in subrecords(addon['data']) if k in (b'MODL',b'RNAM',b'DNAM')]
    assert aaf[b'MOD2']==aaf[b'MOD3']==af[b'MOD2']
    tags=[k for k,v in ap];assert tags.index(b'BOD2')<tags.index(b'RNAM')<tags.index(b'MOD2')<tags.index(b'MOD3')<tags.index(b'MODL')
    assert (ar['form'],1) in contents
    assert (ar['form'],1) in [struct.unpack('<II',v) for k,v in subrecords(allchest['data']) if k==b'CNTO']
    recipe=byform[0x03000000|int(spec['recipe_form'],16)]
    assert U32(dict(subrecords(recipe['data']))[b'CNAM'])==ar['form']
    model=af[b'MOD2'].rstrip(b'\0').decode().replace('\\','/')
    path=ROOT/'data/meshes'/model;n=NifBlocks(path)
    assert n.blocks[1:4]==native_ref.blocks[1:4] and n.blocks[5:7]==native_ref.blocks[5:7]
    assert n.blocks[0][1][4:84]==native_ref.blocks[0][1][4:84]
    assert n.strings[U32(n.blocks[3][1][4:])]==b'SHIELD'
    parts=shapes(n);assert set(parts)=={'AA_ShieldBody','AA_ShieldEdge','AA_ShieldMetal','AA_ShieldGrip'}
    ref=NifBlocks(ROOT/'data/meshes/weapons/arcanearsenal'/('greatsword3'+spec['color']+'.nif'));rp=shapes(ref)
    for name,(si,ti) in parts.items():
        b=n.blocks[si][1]
        if name.endswith(('Body','Edge')):
            ri,rt=rp['AA_Greatsword'+name.removeprefix('AA_Shield')]
            assert b[16:24]==ref.blocks[ri][1][16:24] and b[44:]==ref.blocks[ri][1][44:]
            assert n.blocks[ti]==ref.blocks[rt]
            assert 0<struct.unpack_from('<f',b,56)[0]<=1.450001
        else:assert struct.unpack_from('<f',b,56)[0]==0
        for t in texture_paths(n.blocks[ti][1]):
            if t:assert (ROOT/'data'/t).is_file(),t
    NifFile.clear_log();native=NifFile(str(path))
    assert not NifFile.message_log(),NifFile.message_log()
    assert len(native.shapes)==4
    allverts=[];triangles=0
    for shape in native.shapes:
        vs=shape.verts;allverts.extend(vs);triangles+=len(shape.tris)
        assert all(math.isfinite(v) for p in vs for v in p)
        assert len(shape.uvs)==len(vs) and len(shape.normals)==len(vs)
        for a,b,c in shape.tris:
            assert len({a,b,c})==3 and min(a,b,c)>=0 and max(a,b,c)<len(vs)
            u=[vs[b][i]-vs[a][i] for i in range(3)];v=[vs[c][i]-vs[a][i] for i in range(3)]
            cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            assert sum(x*x for x in cross)>1e-12,(key,'degenerate triangle')
    # Every rendered vertex must lie inside the dropped-item convex hull.
    hull=n.blocks[4][1];nv=struct.unpack_from('<I',hull,32)[0];offset=36+nv*16
    count=struct.unpack_from('<I',hull,offset)[0];assert len(hull)==offset+4+count*16
    planes=[struct.unpack_from('<4f',hull,offset+4+i*16) for i in range(count)]
    assert nv<=255
    for p in allverts:
        assert all(sum(p[i]/69.99125*plane[i] for i in range(3))+plane[3]<.001 for plane in planes),(key,p)
    bounds=struct.unpack('<6h',af[b'OBND'])
    assert all(bounds[i]<=p[i]<=bounds[i+3] for p in allverts for i in range(3))
    reports.append(dict(key=key,armor=90,triangles=triangles,shapes=4,convex_vertices=nv,attachment='SHIELD',male_female_models=True,all_original_races=True))
baseline=ROOT/'build/before-0.53.0/data'
for rel,digest in json.loads((baseline.parent/'manifest.json').read_text()).items():
    assert hashlib.sha256((baseline/rel).read_bytes()).hexdigest()==digest
    if rel!='ArcaneArsenal.esp':assert (ROOT/'data'/rel).read_bytes()==(baseline/rel).read_bytes(),rel
old=list(records(baseline/'ArcaneArsenal.esp'))
for r in old:
    if r['sig']==b'TES4':continue
    current=byform[r['form']]
    if edid(r)=='AAAllBowsTestChest':
        strip=lambda x:[(k,v) for k,v in subrecords(x['data']) if k not in (b'COCT',b'CNTO')]
        assert strip(r)==strip(current)
    else:assert current==r,edid(r)
assert set(byform)-{r['form'] for r in old}=={0x03000000|f for f in range(0xBA0,0xBAD)}
assert not any(0xB00<=(r['form']&0xffffff)<=0xB7F for r in items)
assert len(runtime_paths())==246
for name in ('metal','grip'):
    raw=(ROOT/'data/textures/armor/arcanearsenal'/('shield_'+name+'_d.dds')).read_bytes()
    assert raw[:4]==b'DDS ' and struct.unpack_from('<I',raw,28)[0]==10
report=dict(version='0.53.0',passed=True,shields=reports,previous_runtime_assets_unchanged=True,existing_plugin_records_preserved=True,runtime_files=246,gameplay_tested=False)
(ROOT/'build/shields-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
