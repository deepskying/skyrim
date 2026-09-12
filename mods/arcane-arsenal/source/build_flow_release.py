"""Rebuild the selected flow silhouettes and validate each exported color variant."""
from pathlib import Path
import concurrent.futures,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
BLENDER=ROOT.parents[1]/'reference/bow-tools/blender-4.5.13-windows-x64/blender.exe'
specs=[s for s in json.loads((ROOT/'source/geometric_catalog.json').read_text(encoding='utf-8'))
       if s['design'] in ('plates','hexagon','squares','diamonds','triangles','chevron')]
keys=[s['key'] for s in specs]
if '--keys' in sys.argv:keys=sys.argv[sys.argv.index('--keys')+1].split(',')
assert set(keys)<=set(s['key'] for s in specs)
def run(script,args,tag):
    log=ROOT/'build'/('flow-'+tag+'.log')
    with log.open('w',encoding='utf-8') as stream:
        result=subprocess.run([str(BLENDER),'--background','--threads','4','--python-exit-code','1',
             '--python',str(ROOT/'source'/script),'--',*args],stdout=stream,stderr=subprocess.STDOUT,
             creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError(str(log)+'\n'+log.read_text(encoding='utf-8')[-3000:])
    print(tag+' OK',flush=True)
if '--verify-only' not in sys.argv:
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda key:run('build_geometric.py',[key],key),keys))
    run('build_aries_particles.py',['--geometric','--keys',','.join(keys)],'particles')
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(lambda key:run('verify_rig.py',[key],key+'-rig'),keys))
print('FLOW_BUILD_VERIFIED '+str(len(keys)),flush=True)
