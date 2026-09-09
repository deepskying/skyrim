"""Package only runtime assets and instructions, then verify archive integrity."""
from pathlib import Path
import hashlib
import json
import zipfile

root = Path(__file__).resolve().parents[1]
archive = root / 'packaging/GlacialCrown-0.1.1.zip'
archive.parent.mkdir(parents=True, exist_ok=True)
assets = sorted(p for p in (root / 'data').rglob('*') if p.is_file())
assert assets and (root / 'data/GlacialCrown.esp') in assets
assert all(p.suffix.lower() in {'.esp', '.nif', '.dds'} for p in assets)
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as package:
    for path in assets:
        package.write(path, path.relative_to(root / 'data').as_posix())
    package.write(root / 'README.md', 'README.md')
with zipfile.ZipFile(archive) as package:
    assert package.testzip() is None
    for path in assets:
        assert package.read(path.relative_to(root / 'data').as_posix()) == path.read_bytes()
report = {
    'archive': str(archive),
    'bytes': archive.stat().st_size,
    'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    'runtime_files': len(assets),
    'verified': True,
}
(root / 'build').mkdir(exist_ok=True)
(root / 'build/package-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
