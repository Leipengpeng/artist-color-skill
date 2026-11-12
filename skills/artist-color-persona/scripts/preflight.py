"""Report local prerequisites; host Image capabilities still require a real tool check."""
import importlib.util
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
dependencies = {name: importlib.util.find_spec(name) is not None for name in ('numpy', 'PIL', 'scipy', 'png')}
index = root / 'assets/artworks/index.json'
result = {'python': sys.version.split()[0], 'python_supported': sys.version_info >= (3, 10),
          'skill_root': str(root), 'dependencies': dependencies, 'artwork_index_exists': index.is_file(),
          'image_tool_status': 'must_check_in_host',
          'host_checks': ['can inspect both actual image files', 'can submit both in one edit',
                          'can save the actual returned image file', 'can run Python and return files']}
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(0 if result['python_supported'] and all(dependencies.values()) and index.is_file() else 1)
