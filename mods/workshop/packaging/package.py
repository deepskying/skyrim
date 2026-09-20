"""Build one MO2 mod from the two source modules; never install or edit saves."""
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODS = ROOT.parent
OUT = ROOT / 'packaging/release/EquipmentWorkshop-1.7.3'

def package():
    dll = ROOT / 'native/build/windows/x64/release/EquipmentWorkshop.dll'
    equipment = MODS / 'durability-manager'
    arrows = MODS / 'magic-arrows'
    for required in (dll, equipment / 'web/dist/index.html', equipment / 'packaging/DurabilityManager.esp', arrows / 'data/MagicArrows.esp'):
        if not required.is_file():
            raise RuntimeError(f'Missing build output: {required}')
    # Use a fresh versioned staging tree so retired JS bundles cannot leak in.
    if OUT.exists():
        assert OUT.resolve().is_relative_to((ROOT / 'packaging/release').resolve())
        shutil.rmtree(OUT)
    plugins = OUT / 'SKSE/Plugins'
    plugins.mkdir(parents=True)
    shutil.copy2(dll, plugins / dll.name)
    for name in ('DurabilityManager.ini', 'DurabilityManager.rules.json'):
        shutil.copy2(equipment / 'packaging' / name, plugins / name)
    # The unified workshop owns its entry key; keep standalone defaults intact.
    config = plugins / 'DurabilityManager.ini'
    config.write_text(config.read_text(encoding='utf-8').replace('Key=F\n', 'Key=A\n', 1), encoding='utf-8')
    for name in ('MagicArrows.ini', 'MagicArrows.rules.json'):
        source = arrows / 'data/SKSE/Plugins' / name
        if source.exists(): shutil.copy2(source, plugins / name)
    shutil.copy2(equipment / 'packaging/DurabilityManager.esp', OUT / 'DurabilityManager.esp')
    shutil.copy2(arrows / 'data/MagicArrows.esp', OUT / 'MagicArrows.esp')
    for name in ('meshes', 'textures', 'scripts', 'Scripts'):
        source = arrows / 'data' / name
        if source.exists(): shutil.copytree(source, OUT / name)
    for name in ('EquipmentWorkshop.recycling.json', 'EquipmentWorkshop.recycling.rules.json'):
        shutil.copy2(ROOT / 'data/SKSE/Plugins' / name, plugins / name)
    assert not (OUT / 'SimpleRecycling.esp').exists()
    assert not list(OUT.rglob('zsr*'))
    shutil.copytree(equipment / 'web/dist', OUT / 'PrismaUI/views/DurabilityManager')
    shutil.copytree(equipment / 'web/dist', OUT / 'MeridianUI/equipmentworkshop')
    shutil.copy2(ROOT / 'native/vendor/MeridianUIAPI/LICENSE-MIT', OUT / 'Meridian-SDK-LICENSE.txt')
    shutil.copy2(ROOT / 'README.md', OUT / 'README.md')
    shutil.copy2(ROOT / 'docs/native-recycling-migration.md', OUT / 'NativeRecycling-migration.md')
    (OUT / 'meta.ini').write_text('[General]\ngameName=Skyrim Special Edition\nversion=1.7.3\nnotes=Unified equipment and magic arrow workshop; legacy ESP identities retained.\n', encoding='utf-8')
    assert [p.name for p in plugins.glob('*.dll')] == ['EquipmentWorkshop.dll']
    archive = ROOT / 'packaging/EquipmentWorkshop-1.7.3.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for source in sorted(OUT.rglob('*')):
            if source.is_file(): z.write(source, source.relative_to(OUT))
    print(archive)

if __name__ == '__main__': package()
