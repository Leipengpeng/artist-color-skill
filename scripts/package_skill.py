"""Build portable ZIPs; perform static/package checks only, without running a grade."""
from pathlib import Path
import ast
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/artist-color-persona'
DIST = ROOT / 'dist'

def main():
    for p in SKILL.rglob('*.py'):
        ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
    for p in SKILL.rglob('*.json'):
        json.loads(p.read_text(encoding='utf-8'))
    for required in ('SKILL.md', 'references/doubao-workflow.md', 'scripts/artwork_library.py', 'scripts/export_delivery.py'):
        if not (SKILL / required).is_file(): raise FileNotFoundError(required)
    index = json.loads((SKILL / 'assets/artworks/index.json').read_text(encoding='utf-8'))
    assert len(index) == 10
    count = 0
    bundled = 0
    for entry in index.values():
        manifest = SKILL / 'assets/artworks' / entry['manifest']
        items = json.loads(manifest.read_text(encoding='utf-8'))['items']
        count += len(items)
        for item in items:
            image = manifest.parent / item['file']
            if image.is_file():
                assert item.get('rights', '').startswith('CC0'), image
                assert hashlib.sha256(image.read_bytes()).hexdigest() == item['sha256']
                bundled += 1
    assert count == 80 and bundled == 3
    files = sorted(p for p in SKILL.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    DIST.mkdir(exist_ok=True)
    receipts = []
    for flat, name in [(True, 'artist-color-persona-doubao-v1.0.0.zip'), (False, 'artist-color-persona-v1.0.0.zip')]:
        output = DIST / name
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for source in files:
                relative = source.relative_to(SKILL).as_posix()
                info = zipfile.ZipInfo(relative if flat else 'artist-color-persona/' + relative, (2026, 11, 12, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, source.read_bytes())
        receipts.append({'file': name, 'bytes': output.stat().st_size, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest()})
    result = {'version': '1.0.0', 'artists': 10, 'work_records': count, 'bundled_cc0_images': bundled,
              'validation': 'static syntax, metadata and package integrity only; no independent skill/model trial',
              'archives': receipts}
    (DIST / 'release-manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
