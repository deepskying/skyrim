"""Load reference-contoured solid meshes with dedicated projected UV textures."""
import json
from paths import BUILD
from geometry import Mesh
KEYS=('fire','holy')
VERSION='0.4.0'
def generate(key):
    data=json.loads((BUILD/'faithful-samples-01'/f'{key}-geometry.json').read_text(encoding='utf-8'))
    parts={}
    for name,shape in data.items():
        m=Mesh();m.verts=[tuple(v) for v in shape['verts']];m.tris=[tuple(t) for t in shape['tris']];m.uv=[tuple(v) for v in shape['uv']];parts[name]=m
    return parts
def texture_path(key,part):
    return 'textures\\magicarrows\\faithful01\\'+key+'_'+part+'.dds'
def shader_values(key,part):return (1,1,1),1.65
