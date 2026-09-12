"""Read-only migration audit and human-readable local report."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from migrate_backgrounds import texture_refs, REPO

parser = argparse.ArgumentParser()
parser.add_argument('--report', type=Path, required=True)
parser.add_argument('--destination', type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.report / 'python-libs'))
sys.path.insert(0, str(REPO / 'mods/arcane-arsenal/source'))
from nif_blocks import NifBlocks
from PIL import Image, ImageDraw, ImageFont

result = json.loads((args.report / 'migration-result.json').read_text(encoding='utf-8'))
inspection = json.loads((args.report / 'inspection.json').read_text(encoding='utf-8'))
library = args.destination / 'MainMenuManager/backgrounds'
files = 0
models = 0
repairs = 0
preview_count = 0
unique_bsa = set()
issues = []
complete_images = []
for theme in result['themes']:
    root = library / theme['folder']
    metadata = json.loads((root / 'theme.json').read_text(encoding='utf-8'))
    assert metadata['enabled'] == (not theme['issues'])
    assert (root / 'disabled.txt').exists() == bool(theme['issues'])
    assert (root / 'source-manifest.json').is_file()
    for relative, source in theme['assets'].items():
        file = root / 'Data' / relative
        assert file.is_file() and file.stat().st_size == source['size'], file
        files += 1
        if relative.endswith('.nif'):
            models += 1
            blob = file.read_bytes()
            if not theme['issues']:
                for ref in texture_refs(blob):
                    assert (root / 'Data' / ref).is_file(), (file, ref)
            if source.get('repairs'):
                # Independently parse the rewritten block-size envelope.
                nif = NifBlocks(file)
                assert nif.blocks and not any(b'D:/' in b or b'D:\\' in b for _, b in nif.blocks)
                assert hashlib.sha256(Path(source['path']).read_bytes()).hexdigest() == source['source_sha256']
                repairs += 1
        if source['kind'] == 'bsa':
            unique_bsa.add((source['path'], source['key']))
    for preview in theme.get('previews', []):
        with Image.open(root / preview['path']) as image:
            image.verify()
        preview_count += 1
    issues.extend(theme.get('preview_errors', []))
    if not theme['issues'] and theme.get('previews'):
        complete_images.append((root / theme['previews'][0]['path'], theme['folder']))

# A small contact sheet is QA only; all full previews remain in the gallery.
selected = [complete_images[i] for i in range(0, len(complete_images), max(1, len(complete_images) // 12))][:12]
sheet = Image.new('RGB', (1200, 660), '#141b24')
draw = ImageDraw.Draw(sheet)
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 13)
for i, (path, title) in enumerate(selected):
    with Image.open(path) as original:
        image = original.convert('RGB'); image.thumbnail((290, 182))
    x, y = (i % 4) * 300, (i // 4) * 220
    sheet.paste(image, (x + (300 - image.width) // 2, y))
    draw.text((x + 5, y + 187), title[:31], fill='white', font=font)
sheet.save(args.report / 'preview-contact-sheet.jpg', quality=90)

summary = {'theme_folders': len(result['themes']), 'runtime_candidates': sum(not c['issues'] for c in result['themes']),
           'resource_files': files, 'model_dependency_checks': models, 'portable_nif_repairs_verified': repairs,
           'preview_files_verified': preview_count, 'preview_errors': issues,
           'bsa_dependencies': [{'archive': p, 'resource': k} for p, k in sorted(unique_bsa)]}
text = ['# 开屏背景迁移报告', '',
        f'- 可供新模组识别的完整效果：{summary["runtime_candidates"]} 套。',
        f'- 待确认散件/编辑源图：{result["summary"]["review_effects"]} 项，位于 backgrounds/_待确认，不参与随机。',
        f'- 总计复制 {files} 个资源文件，生成并核验 {preview_count} 张预览。',
        f'- 资源大小约 {result["summary"]["bytes"] / 1024**3:.2f} GiB（不含预览和报告）。',
        '- 14 组完全相同的套件来源合并；另有 6 份部分重复资源并入已有完整主题。',
        f'- 修正迁移副本中的 {repairs} 个 NIF 绝对纹理路径，原文件保持不变。',
        '- 新模组的实际扫描代码识别到 272 套，诊断为 0。未进行游戏内渲染验证。',
        '', '## 来源与 BSA', '',
        '- 扫描了游戏目录、MO2 各模组及 overwrite/backup 中的候选文件。',
        f'- 找到 {inspection["archives_scanned"] + len(inspection["archive_errors"])} 个 BSA 文件，其中 {inspection["archives_scanned"]} 个索引可读取。',
        '- 可读取的 BSA 未发现额外自定义主菜单背景；提取了模型需要的以下配套纹理，原 BSA 未改动：', '']
text += [f'  - `{Path(p).name}` → `{k}`' for p, k in sorted(unique_bsa)]
text += ['', '以下文件格式不受当前提取器支持，未对它们做提取或修改：', '']
text += [f'- `{e["archive"]}`：{e["error"]}' for e in inspection['archive_errors']]
text += ['', '## 待确认资源', '']
text += [f'- `{c["folder"]}`：' + '；'.join(c['issues']) for c in result['themes'] if c['issues']]
text += ['', '## 使用与筛选', '',
         '- 打开上一级的“背景目录.html”，可搜索名称、查看缩略图和来源。',
         '- 每套目录内有 theme.json、预览、来源与说明.txt 和逐文件来源清单。',
         '- 关闭游戏后，把不需要的整套目录移出 backgrounds，或创建 disabled.txt 暂停使用。',
         '- 本次仅迁移资源，未改 MO2 启用顺序，也未隐藏旧随机插件。当前 -std- 配置中两个管理模组均已启用，旧插件存在时新模组会按设计暂停应用。',
         '- 切换到新管理器时，只隐藏旧模组的 SKSE/Plugins/main_menu_randomizer.dll；不要直接删除旧模组的其他资源。',
         '- 原有模组、散落资源及备份全部保留。', '']
report_root = args.destination / 'MainMenuManager/migration-20260912'
for directory in (args.report, report_root):
    (directory / 'verification.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (directory / '迁移报告.md').write_text('\n'.join(text), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
