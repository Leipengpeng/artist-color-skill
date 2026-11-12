"""Resolve curated artwork metadata and private reference files; never invent an image."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import os
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / 'assets/artworks'
CACHE = Path(os.environ.get('ARTIST_COLOR_CACHE', str(Path.home() / '.cache/artist-color-persona')))

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def manifest(artist):
    index = load(LIBRARY / 'index.json')
    if artist not in index:
        raise ValueError('Unknown artist ID. Choose an ID from assets/artworks/index.json')
    p = LIBRARY / index[artist]['manifest']
    return p, load(p)

def selected(artist, filename):
    p, m = manifest(artist)
    matches = [x for x in m['items'] if x['file'] == filename]
    if len(matches) != 1:
        raise ValueError('The --file value must exactly match one curated manifest item')
    return p, matches[0]

def resolved(artist, p, item):
    bundled = p.parent / item['file']
    if bundled.is_file():
        if digest(bundled) != item['sha256']:
            raise ValueError(f'Bundled image hash mismatch: {bundled}')
        return str(bundled.resolve()), 'bundled'
    receipt = CACHE / artist / (item['file'] + '.json')
    if receipt.is_file():
        r = load(receipt)
        image = Path(r['path'])
        if not image.is_file() or digest(image) != r['sha256']:
            raise ValueError(f'Private cache changed: {image}; import or fetch again to a new cache')
        return str(image.resolve()), r['method']
    return None, 'needs_fetch_or_import'

def save_private(artist, item, data, suffix, method, source):
    from PIL import Image
    with Image.open(io.BytesIO(data)) as im:
        im.verify()
    folder = CACHE / artist
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (Path(item['file']).stem + suffix.lower())
    expected = hashlib.sha256(data).hexdigest()
    if target.exists() and digest(target) != expected:
        raise FileExistsError(f'Existing private reference differs: {target}. Use another ARTIST_COLOR_CACHE directory.')
    if not target.exists():
        temp = target.with_suffix(target.suffix + '.tmp')
        temp.write_bytes(data)
        temp.replace(target)
    r = {'artist': artist, 'file': item['file'], 'title': item['title'], 'path': str(target.resolve()),
         'sha256': expected, 'source': source, 'rights': item.get('rights', 'See original source'), 'method': method}
    (folder / (item['file'] + '.json')).write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding='utf-8')
    return r

def fetch(artist, filename, open_only=False):
    from PIL import Image, ImageOps, ImageCms
    p, item = selected(artist, filename)
    path, method = resolved(artist, p, item)
    if path:
        return {'path': path, 'method': method, 'title': item['title']}
    if open_only and not item.get('rights', '').startswith('CC0'):
        raise ValueError('download-open only handles manifest entries explicitly marked CC0')
    url = item['image_url']
    if urlsplit(url).scheme != 'https' or '.pdf' in urlsplit(url).path.lower():
        raise ValueError('This reference needs manual extraction/import of the exact artwork; see source_url')
    request = urllib.request.Request(url, headers={'User-Agent': 'artist-color-skill/1.0 (reference retrieval)'})
    with urllib.request.urlopen(request, timeout=30) as response:
        if urlsplit(response.geturl()).scheme != 'https':
            raise ValueError('Insecure reference redirect')
        data = response.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024:
        raise ValueError('Reference exceeds the 32 MiB fetch limit; import a local image instead')
    expected = item.get('source_asset_sha256')
    if expected and hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Source bytes changed. Inspect the current artwork and import it explicitly; do not substitute silently.')
    with Image.open(io.BytesIO(data)) as im:
        profile = im.info.get('icc_profile')
        im = ImageOps.exif_transpose(im)
        if profile:
            im = ImageCms.profileToProfile(im.convert('RGB'), ImageCms.ImageCmsProfile(io.BytesIO(profile)),
                                          ImageCms.createProfile('sRGB'), outputMode='RGB')
        else:
            im = im.convert('RGB')
        crop = item.get('source_artwork_crop')
        if crop:
            if len(crop) != 4 or not (0 <= crop[0] < crop[2] <= 1 and 0 <= crop[1] < crop[3] <= 1):
                raise ValueError('Invalid curated crop')
            im = im.crop(tuple(round(v * (im.width if i % 2 == 0 else im.height)) for i, v in enumerate(crop)))
        im.thumbnail((720, 720), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        im.save(output, format='PNG')
    return save_private(artist, item, output.getvalue(), '.png', 'fetched_private_reference', url)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('list'); p.add_argument('--artist', required=True)
    p = sub.add_parser('import'); p.add_argument('--artist', required=True); p.add_argument('--file', required=True); p.add_argument('--image', type=Path, required=True)
    p = sub.add_parser('fetch'); p.add_argument('--artist', required=True); p.add_argument('--file', required=True)
    p = sub.add_parser('download-open'); p.add_argument('--artist', required=True)
    sub.add_parser('check')
    args = parser.parse_args()
    if args.action == 'list':
        p, m = manifest(args.artist)
        result = []
        for item in m['items']:
            path, method = resolved(args.artist, p, item)
            result.append({**item, 'local_path': path, 'availability': method})
    elif args.action == 'import':
        _, item = selected(args.artist, args.file)
        result = save_private(args.artist, item, args.image.read_bytes(), args.image.suffix, 'user_imported_reference', str(args.image.resolve()))
    elif args.action == 'fetch':
        result = fetch(args.artist, args.file)
    elif args.action == 'download-open':
        _, m = manifest(args.artist)
        result = [fetch(args.artist, x['file'], open_only=True) for x in m['items'] if x.get('rights', '').startswith('CC0')]
    else:
        result = []
        for artist in load(LIBRARY / 'index.json'):
            p, m = manifest(artist)
            items = [resolved(artist, p, x) for x in m['items']]
            result.append({'artist': artist, 'works': len(items), 'available': sum(x[0] is not None for x in items)})
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        raise SystemExit(f'Artwork library stopped: {error}') from None
