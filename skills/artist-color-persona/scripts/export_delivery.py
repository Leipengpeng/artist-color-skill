"""Export an existing verified job in the original/artwork/Image/LUT order."""
import argparse
import json
import shutil
from pathlib import Path
from color_match_lut import digest

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    job = read(args.job)
    result = read(args.job.parent / 'result.json')
    entries = [('00_original', job['original']), ('01_artwork', job['artwork']['archived']),
               ('02_Image', result['image_return']), ('03_LUT_full_resolution', result['render']),
               ('04_LUT', result['lut'])]
    planned = []
    for label, record in entries:
        source = Path(record['path'])
        if digest(source) != record['sha256']:
            raise ValueError(f'Input changed: {source}')
        target = args.output / (label + source.suffix.lower())
        if target.exists() and digest(target) != record['sha256']:
            raise FileExistsError(f'Delivery already contains a different file: {target}')
        planned.append((source, target, record['sha256']))
    args.output.mkdir(parents=True, exist_ok=True)
    for source, target, expected in planned:
        if not target.exists(): shutil.copyfile(source, target)
        if digest(target) != expected: raise ValueError(f'Copy failed: {target}')
    manifest = {'artist': job['artist'], 'artwork': job['artwork']['title'],
                'artwork_source': job['artwork']['source'], 'selection_reason': job['artwork']['selection_reason'],
                'actual_image_prompt': Path(job['prompt']['path']).read_text(encoding='utf-8'),
                'fit_scope': result['fit_scope'], 'geometry': result['geometry'], 'size': result['render']['size'],
                'files': [{'file': p.name, 'sha256': h} for _, p, h in planned]}
    (args.output / 'delivery.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(args.output.resolve()), 'files': len(planned)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
