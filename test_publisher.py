"""Offline schema checks for the one-file release publisher."""
from pathlib import Path
import tempfile
import shutil
import subprocess
import sys
import build

def fixture(folder,name,text):
    content=folder/'content';content.mkdir(exist_ok=True)
    (content/name).write_text(text)

original=build.ROOT
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);build.ROOT=root
    fixture(root,'2026-09-11-example.md','---\ndate: 2026-09-11\ntype: daily\ntitle: Выпуск\n---\n# Выпуск\n\n## Раздел\n\nТекст.\n')
    item=build.releases()[0]
    assert item['label']=='Суточный выпуск' and item['count'] is None and item['window']=='2026-09-11'
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);build.ROOT=root
    fixture(root,'bad.md','---\ndate: yesterday\ntype: daily\ntitle: Выпуск\n---\n# Выпуск\n')
    try:build.releases()
    except ValueError as error:assert 'invalid date' in str(error)
    else:raise AssertionError('invalid metadata accepted')
build.ROOT=original
with tempfile.TemporaryDirectory() as temp:
    checkout=Path(temp)/'site'
    shutil.copytree(original,checkout,ignore=shutil.ignore_patterns('.git','_site','__pycache__'))
    fixture(checkout,'2026-09-11-one-file.md','---\ndate: 2026-09-11\ntype: daily\ntitle: Один файл\n---\n# Один файл\n\n## Раздел\n\nПроверка. [Источник](https://example.com/source)\n')
    subprocess.run([sys.executable,'build.py'],cwd=checkout,check=True,capture_output=True,text=True)
    subprocess.run([sys.executable,'check.py'],cwd=checkout,check=True,capture_output=True,text=True)
    assert (checkout/'_site/2026-09-11-one-file.html').is_file()
    for page in ('index.html','archive.html'):
        assert '2026-09-11-one-file.html' in (checkout/'_site'/page).read_text()
print('PASS: minimal one-file metadata and invalid metadata rejection')
