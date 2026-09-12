"""Create larger viewing copies inside migrated theme folders, leaving DDS unchanged."""
import argparse
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--library', type=Path, required=True)
parser.add_argument('--pillow', type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.pillow))
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image

count = 0
for metadata in args.library.glob('**/theme.json'):
    theme = metadata.parent
    if theme.name.startswith('_'):
        continue
    data = json.loads(metadata.read_text(encoding='utf-8-sig'))
    for preview in data.get('previews', []):
        source = theme / 'Data' / preview['resource']
        output = theme / (Path(preview['path']).stem + '-large.jpg')
        if not source.resolve().is_relative_to(theme.resolve()) or not output.resolve().is_relative_to(theme.resolve()):
            raise ValueError('Preview path escapes theme')
        if output.exists():
            continue
        with Image.open(source) as original:
            image = original.convert('RGB')
            image.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
            image.save(output, quality=93)
        count += 1
        if count % 50 == 0:
            print(f'Created {count} large previews', flush=True)
print(f'Finished: {count} large previews')
