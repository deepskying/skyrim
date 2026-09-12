"""Actual source-mesh grip comparison under neutral studio light, without bloom.

This view intentionally shows geometry rather than claiming to reproduce ENB.
The source blend and all runtime shader settings are left untouched.
"""
from pathlib import Path
import bpy,bmesh,math,sys
ROOT=Path(__file__).resolve().parents[1]
items=[('redplates','叠弦'),('geohexagonred','六垣'),('geosquaresred','方旋'),('reddiamonds','流菱')]
remaining='--remaining' in sys.argv
if remaining:items=[('redtriangles','旋序'),('geochevronred','锋羽')]
gemini='--gemini' in sys.argv
if gemini:items=[('geminired','余烬·双子'),('geminigreen','流萤·双子'),('geminiblue','寒汐·双子'),('geminipurple','梦隙·双子')]
cancer='--cancer' in sys.argv
if cancer:items=[('cancerred','余烬·巨蟹'),('cancergreen','流萤·巨蟹'),('cancerblue','寒汐·巨蟹'),('cancerpurple','梦隙·巨蟹')]
leo='--leo' in sys.argv
if leo:items=[('leored','余烬·狮子'),('leogreen','流萤·狮子'),('leoblue','寒汐·狮子'),('leopurple','梦隙·狮子')]
virgo='--virgo' in sys.argv
if virgo:items=[('virgored','余烬·处女'),('virgogreen','流萤·处女'),('virgoblue','寒汐·处女'),('virgopurple','梦隙·处女')]
libra='--libra' in sys.argv
if libra:items=[('librared','余烬·天秤'),('libragreen','流萤·天秤'),('librablue','寒汐·天秤'),('librapurple','梦隙·天秤')]
sagittarius='--sagittarius' in sys.argv
if sagittarius:items=[('sagittariusred','余烬·射手'),('sagittariusgreen','流萤·射手'),('sagittariusblue','寒汐·射手'),('sagittariuspurple','梦隙·射手')]
capricorn='--capricorn' in sys.argv
if capricorn:items=[('capricornred','余烬·摩羯'),('capricorngreen','流萤·摩羯'),('capricornblue','寒汐·摩羯'),('capricornpurple','梦隙·摩羯')]
aquarius='--aquarius' in sys.argv
if aquarius:items=[('aquariusred','余烬·水瓶'),('aquariusgreen','流萤·水瓶'),('aquariusblue','寒汐·水瓶'),('aquariuspurple','梦隙·水瓶')]
pisces='--pisces' in sys.argv
if pisces:items=[('piscesred','余烬·双鱼'),('piscesgreen','流萤·双鱼'),('piscesblue','寒汐·双鱼'),('piscespurple','梦隙·双鱼')]
scorpio='--scorpio' in sys.argv
if scorpio:items=[('scorpiored','余烬·天蝎'),('scorpiogreen','流萤·天蝎'),('scorpioblue','寒汐·天蝎'),('scorpiopurple','梦隙·天蝎')]
heteromorphic='--heteromorphic' in sys.argv
if heteromorphic:items=[('heteromorphicred', '余烬·断层'), ('heteromorphicgreen', '流萤·繁枝'), ('heteromorphicblue', '寒汐·环阵'), ('heteromorphicpurple', '梦隙·扇阙')]
start=38*(len(items)-1)/2
stem='geometric-grips-remaining' if remaining else 'geometric-grips'
if gemini:stem='gemini-grips'
if cancer:stem='cancer-grips'
if leo:stem='leo-grips'
if virgo:stem='virgo-grips'
if libra:stem='libra-grips'
if sagittarius:stem='sagittarius-grips'
if capricorn:stem='capricorn-grips'
if aquarius:stem='aquarius-grips'
if pisces:stem='pisces-grips'
if scorpio:stem='scorpio-grips'
if heteromorphic:stem='heteromorphic-grips'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;font=bpy.data.fonts.load(r'C:\Windows\Fonts\msyh.ttc')
for i,(key,label) in enumerate(items):
    with bpy.data.libraries.load(str(ROOT/'art'/(key+'.blend'))) as (available,loaded):
        prefix='AA_Heteromorphic' if heteromorphic else 'AA_Scorpio' if scorpio else 'AA_Pisces' if pisces else 'AA_Aquarius' if aquarius else 'AA_Capricorn' if capricorn else 'AA_Sagittarius' if sagittarius else 'AA_Libra' if libra else 'AA_Virgo' if virgo else 'AA_Leo' if leo else 'AA_Cancer' if cancer else 'AA_Gemini' if gemini else 'AA_Geometric'
        loaded.objects=[n for n in available.objects if n in (prefix+'Body',prefix+'Edge',key+'_ROOT',key+'_Rig')]
    for obj in loaded.objects:
        scene.collection.objects.link(obj)
        if obj.parent is None:obj.location.x+=start-i*38
        if obj.type=='MESH':
            # Crop only this disposable preview copy, leaving room for labels.
            obj.data=obj.data.copy();mesh=bmesh.new();mesh.from_mesh(obj.data)
            bmesh.ops.delete(mesh,geom=[v for v in mesh.verts if abs(v.co.y)>27],context='VERTS')
            mesh.to_mesh(obj.data);mesh.free()
    text=bpy.data.curves.new(key+'_label','FONT');text.body=label;text.font=font;text.size=3;text.align_x='CENTER'
    obj=bpy.data.objects.new(key+'_label',text);scene.collection.objects.link(obj)
    obj.location=(start-i*38,-32,-10);obj.rotation_euler=(0,math.pi,0)
cd=bpy.data.cameras.new('Grip comparison');cam=bpy.data.objects.new('Grip comparison',cd);scene.collection.objects.link(cam)
cam.location=(0,0,-240);cam.rotation_euler=(math.pi,0,math.pi);cd.type='ORTHO';cd.ortho_scale=86 if remaining else 157;scene.camera=cam
scene.render.engine='BLENDER_WORKBENCH'
shading=scene.display.shading;shading.light='STUDIO';shading.color_type='SINGLE'
shading.single_color=(.58,.62,.68);shading.show_shadows=True;shading.show_cavity=True
shading.cavity_type='BOTH';shading.curvature_ridge_factor=1.4;shading.curvature_valley_factor=1.1
shading.background_type='WORLD';scene.world.color=(.035,.035,.035)
scene.render.resolution_x=1320 if remaining else 2400;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.use_nodes=False
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'build'/(stem+'-comparison.blend')))
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'build'/(stem+'-comparison.blend')))
scene=bpy.context.scene;scene.render.filepath=str(ROOT/'art'/(stem+'-front.png'))
bpy.ops.render.render(write_still=True)
for key,label in items:
    bpy.data.objects[key+'_ROOT'].rotation_euler.y=math.radians(25)
bpy.context.view_layer.update()
scene.render.filepath=str(ROOT/'art'/(stem+'-oblique.png'));bpy.ops.render.render(write_still=True)
