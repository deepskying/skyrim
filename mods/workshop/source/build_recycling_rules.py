"""Create workshop-owned recycling data from vanilla editor IDs; no mod dependency."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'magic-arrows/source'))
from plugin_records import records, edid

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('C:/Users/linos/Desktop/games/+skyrim/SkyrimSE/Data')
OUT = ROOT / 'data/SKSE/Plugins'
OUT.mkdir(parents=True, exist_ok=True)

def ref(id, plugin='Skyrim.esm'):
    return {'plugin': plugin, 'id': id}

groups = [
    ('dwemer', ('DwarvenBowl','DwarvenPot','DwarvenUrn','DwarvenHigh','DwarvenScrap','DwarvenLargeScrap','DwarvenPlateMetal','DwarvenCog','DwarvenGear','DwarvenGyro','DwarvenKnife','DwarvenSpoon','DwarvenFork','DwarvenCenturionDynamo'), ref(0xDB8A2)),
    ('silverware', ('SilverBowl','SilverPlate','SilverPlatter','SilverGoblet','SilverCandle','SilverJug'), ref(0x5ACDF)),
    ('pottery', ('GlazedBowl','GlazedPlate','GlazedCup','GlazedGoblet'), ref(0x3043,'HearthFires.esm')),
    ('wood', ('BasicWooden','Basket','Broom','Bucket','BasicTankard'), ref(0x6F993)),
    ('ironware', ('BasicPlate','BasicPot','BasicSpoon','BasicFork','BasicKnife','RuinsEmbalming'), ref(0x71CF3)),
    ('cloth', ('RuinsLinenPile',), ref(0x800E4)),
]
compiled = [{'name': name, 'items': [], 'output': output, 'weightRatio': .2} for name, _, output in groups]
for record in records(DATA / 'Skyrim.esm', {b'MISC'}):
    editor = edid(record)
    for index, (_, prefixes, _) in enumerate(groups):
        if editor.startswith(prefixes):
            compiled[index]['items'].append(ref(record['form'] & 0xFFFFFF))
            break

rules = []
def rule(output, *, type=None, keyword=None, ratio=.01, value=False):
    entry = {'output': output, 'weightRatio': ratio}
    if type is not None: entry['formType'] = type
    if keyword: entry['keyword'] = keyword
    if value: entry['useItemValue'] = True
    rules.append(entry)

rule(ref(0xF), type=32, keyword='VendorItemGem', value=True)
rule(ref(0xDB5D2), type=32, keyword='VendorItemAnimalHide', ratio=.2)
rule(ref(0xBFB09), type=32, keyword='VendorItemFirewood', ratio=.2)
rule(ref(0x34CDF), type=46, keyword='VendorItemFood')
rule(ref(0x5A69, 'HearthFires.esm'), type=46)
rule(ref(0x33761), type=23)
rule(ref(0x33761), type=27)
rule(ref(0x6F993), type=31)
rule(ref(0x67181), type=52, ratio=3)
materials = [('Daedric',0x5AD9D),('Dragonbone',0x3ADA4),('Dragonplate',0x3ADA4),('Dragonscale',0x3ADA3),
    ('Dwarven',0xDB8A2),('Ebony',0x5AD9D),('Elven',0x5AD9F),('Glass',0x5ADA1),('Orcish',0x5AD99),
    ('Silver',0x5ACE3),('Steel',0x5ACE5),('Iron',0x5ACE4),('Draugr',0x5ACE4)]
for material, id in materials:
    rule(ref(id), type=41, keyword='WeapMaterial'+material, ratio=.1)
    rule(ref(id), type=26, keyword='ArmorMaterial'+material, ratio=.05)
rule(ref(0x2B06B,'Dragonborn.esm'), type=41, keyword='DLC2WeaponMaterialStalhrim', ratio=.1)
rule(ref(0x2B06B,'Dragonborn.esm'), type=26, keyword='DLC2ArmorMaterialStalhrimHeavy', ratio=.05)
rule(ref(0x2E4E2), type=41, keyword='WeapTypeStaff')
rule(ref(0x5ACDF), type=26, keyword='VendorItemJewelry', ratio=.05)
rule(ref(0x800E4), type=41, ratio=.1)
rule(ref(0x800E4), type=26, ratio=.05)
rule(ref(0x6F993), type=42)
payload = {'version':1,'groups':compiled,'rules':rules}
# Validate every reference against the actual base-game records before publishing rules.
available = {}
for record in [r['output'] for r in rules] + [g['output'] for g in compiled]:
    plugin = record['plugin']
    if plugin not in available: available[plugin] = {r['form'] & 0xFFFFFF for r in records(DATA / plugin)}
    assert record['id'] in available[plugin], record
(OUT/'EquipmentWorkshop.recycling.rules.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'EquipmentWorkshop.recycling.json').write_text(json.dumps({'keyCode':184,'safetyCode':184,'enabled':True,'holdToRecycleStack':True},indent=2)+'\n',encoding='utf-8')
print(f'Created {sum(len(g["items"]) for g in compiled)} clutter mappings and {len(rules)} category/keyword rules.')
