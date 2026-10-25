"""Working selections stay discoverable without replacing a calendar weekly."""
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile

original=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as temp:
    checkout=Path(temp)/'site'
    shutil.copytree(original,checkout,ignore=shutil.ignore_patterns('.git','_site','__pycache__'))
    slug='2026-10-25-working-fixture'
    (checkout/'content'/f'{slug}.md').write_text('---\ndate: 2026-10-25\ntype: working\ntitle: Рабочая подборка\ncount: 1\nsections: 2\n---\n# Рабочая подборка\n\n### Тема\n\nПодробный разбор. [Источник](https://example.com/working-source)\n\n#### Первая часть\n\nПервый механизм.\n\n#### Вторая часть\n\nВторой механизм.\n\n## Что из этого применить в платформе\n\nНичего практического для платформы в этом выпуске не нашли\n\n## Все находки выпуска\n\n1. [Тема](https://example.com/working-source)\n')
    subprocess.run([sys.executable,'build.py'],cwd=checkout,check=True,capture_output=True,text=True)
    subprocess.run([sys.executable,'check.py'],cwd=checkout,check=True,capture_output=True,text=True)
    assert (checkout/'_site'/f'{slug}.html').is_file()
    reader=(checkout/'_site'/f'{slug}.html').read_text()
    assert '<header class="article-head"><p class="eyebrow">Рабочая подборка</p>' in reader
    assert '<h4>Первая часть</h4>' in reader and '<h4>Вторая часть</h4>' in reader
    assert reader.count('href="#section-')==3, 'internal H4 must not become edition topics'
    archive=(checkout/'_site'/'findings.html').read_text()
    assert 'Первый механизм.' in archive and 'Второй механизм.' in archive, 'H4 must retain full topic text in findings'
    for page in ('index.html','archive.html'):
        text=(checkout/'_site'/page).read_text()
        assert f'{slug}.html' in text and 'Рабочая подборка' in text
        assert text.index('2026-10-25-weekly.html')<text.index(f'{slug}.html'), 'working selection replaced calendar weekly'
print('PASS: working selection is distinct, discoverable and follows calendar weekly')
