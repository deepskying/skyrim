"""Drop unreferenced bundles from an installed EquipmentWorkshop copy.

Every install copies a fresh hashed bundle into the two view folders, so old bundles
pile up until the mod folder no longer mirrors the release tree. This keeps only the
assets the current index.html references and never touches configs, ESPs or meshes.
"""
from pathlib import Path
import json
import re
import subprocess
import sys

VIEWS = (Path('PrismaUI/views/DurabilityManager'), Path('MeridianUI/equipmentworkshop'))

def mod_folder():
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    state = json.loads((Path(__file__).resolve().parent / 'local-install-state.json').read_text(encoding='utf-8'))
    return Path(state['mod']).resolve()

def prune(mod):
    running = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         'Get-Process SkyrimSE,skse64_loader -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName'],
        capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip()
    if running:
        raise SystemExit('Close Skyrim before pruning: ' + running)
    removed = freed = 0
    for view in VIEWS:
        assets = mod / view / 'assets'
        keep = set(re.findall(r'\./assets/([^"\']+)', (mod / view / 'index.html').read_text(encoding='utf-8')))
        for path in sorted(assets.iterdir()):
            if not path.is_file() or path.name in keep:
                continue
            if not re.fullmatch(r'index-[\w.-]+\.(js|css)', path.name):
                raise SystemExit(f'Refusing to remove unexpected file: {path}')
            if mod not in path.resolve().parents:
                raise SystemExit(f'Refusing to remove outside {mod}: {path}')
            freed += path.stat().st_size
            path.unlink()
            removed += 1
        missing = sorted(name for name in keep if not (assets / name).is_file())
        if missing:
            raise SystemExit(f'{view} is missing referenced assets: {missing}')
    print(f'Removed {removed} stale bundle(s), {freed / 1048576:.2f} MB; {mod} keeps one bundle per view.')

if __name__ == '__main__':
    prune(mod_folder())
