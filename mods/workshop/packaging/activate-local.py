"""Activate the prepared local installation after MO2 and Skyrim have exited."""
from pathlib import Path
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
state = json.loads((ROOT / 'local-install-state.json').read_text(encoding='utf-8'))
profile = Path(state['profile']).resolve()
mod = Path(state['mod']).resolve()
mo = profile.parents[1]
assert profile == (mo / 'profiles/-std-').resolve()
assert mod.parent == (mo / 'mods').resolve()
assert (mod / 'SKSE/Plugins/EquipmentWorkshop.dll').is_file()
running = subprocess.run([
    'powershell', '-NoProfile', '-Command',
    "Get-Process ModOrganizer,SkyrimSE,skse64_loader -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName"
], capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
if running.strip():
    raise SystemExit('Close MO2 and Skyrim before activating: ' + running.strip())
backup = Path(state['backup']) / 'before-activation'
backup.mkdir(exist_ok=True)
for filename in ('modlist.txt', 'plugins.txt', 'loadorder.txt'):
    shutil.copy2(profile / filename, backup / filename)
old_names = {
    '玩法改进-耐久度系统-DurabilityManager-🟩shift+F',
    '武器魔法-魔法箭工坊-Magic Arrows',
}
path = profile / 'modlist.txt'
lines = path.read_text(encoding='utf-8-sig').splitlines()
lines = [('-' + line[1:]) if line[:1] in '+-' and line[1:] in old_names else line
         for line in lines if line[1:] != state['name']]
lines.insert(1 if lines and lines[0].startswith('#') else 0, '+' + state['name'])
path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
plugins = ('MagicArrows.esp', 'DurabilityManager.esp')
for filename in ('plugins.txt', 'loadorder.txt'):
    path = profile / filename
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    lines = [line for line in lines if line.lstrip('*').lower() not in {p.lower() for p in plugins}]
    # The previous game's SKSE load map places these after ArcaneArsenal,
    # before MusicManager. Preserve every unrelated plugin's state and order.
    anchor = next((i + 1 for i, line in enumerate(lines) if line.lstrip('*').lower() == 'arcanearsenal.esp'), len(lines))
    lines[anchor:anchor] = [('*' if filename == 'plugins.txt' else '') + p for p in plugins]
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('Activated EquipmentWorkshop 1.0.5 in -std-; legacy DLL mods disabled and both ESPs enabled.')
