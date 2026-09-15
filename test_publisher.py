"""Offline schema checks for the one-file release publisher."""
from pathlib import Path
import json
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
with tempfile.TemporaryDirectory() as temp:
    checkout=Path(temp)/'site'
    shutil.copytree(original,checkout,ignore=shutil.ignore_patterns('.git','_site','__pycache__'))
    comparisons=checkout/'comparisons'; comparisons.mkdir(exist_ok=True)
    (comparisons/'published.json').write_text(json.dumps({'schema_version':1,'comparisons':[{'id':'2026-09-14-ab','date':'2026-09-14','title':'Слепое сравнение','variants':[{'label':'A','file':'2026-09-14-blind-a.md','slug':'comparison-2026-09-14-blind-a'},{'label':'B','file':'2026-09-14-blind-b.md','slug':'comparison-2026-09-14-blind-b'}]}]},ensure_ascii=False))
    for label in ('a','b'):
        (comparisons/f'2026-09-14-blind-{label}.md').write_text('---\ndate: 2026-09-14\ntitle: Вариант '+label.upper()+'\n---\n# Вариант '+label.upper()+'\n\n## Раздел\n\n[Источник](https://example.com/'+label+')\n')
    (comparisons/'2026-09-13-blind-a.md').write_text('raw historical comparison must remain GitHub-only')
    subprocess.run([sys.executable,'build.py'],cwd=checkout,check=True,capture_output=True,text=True)
    subprocess.run([sys.executable,'check.py'],cwd=checkout,check=True,capture_output=True,text=True)
    assert (checkout/'_site'/'comparisons.html').is_file()
    assert (checkout/'_site'/'comparison-2026-09-14-blind-a.html').is_file()
    assert not (checkout/'_site'/'2026-09-13-blind-a.html').exists()
    for page in ('index.html','archive.html'):
        assert 'comparison-2026-09-14-blind-a.html' not in (checkout/'_site'/page).read_text()
    manifest_path=comparisons/'published.json'; manifest=json.loads(manifest_path.read_text())
    manifest['comparisons'].append(manifest['comparisons'][0])
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False))
    rejected=subprocess.run([sys.executable,'build.py'],cwd=checkout,capture_output=True,text=True)
    assert rejected.returncode!=0 and 'exactly one A/B pair' in rejected.stderr
print('PASS: minimal one-file metadata and invalid metadata rejection')
