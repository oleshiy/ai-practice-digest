"""A thematic weekly preserves topics, the complete list, and the practical section."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
READER='''---
date: 2026-10-18
type: weekly
title: Тематический выпуск
count: 2
details: 1
shorts: 1
sections: 3
---
# Тематический выпуск

### Проверка результата

Конкретный опыт. [Источник](https://example.com/first)

## Как контролировать действия

### Граница доступа

Другой механизм. [Источник](https://example.com/second)

## Что из этого применить в платформе

1. Проверить права в пилоте.

## Все находки выпуска

1. [Проверка результата](https://example.com/first)

2. [Граница доступа](https://example.com/second)
'''

def run(folder,name):
    return subprocess.run([sys.executable,name],cwd=folder,capture_output=True,text=True)

with tempfile.TemporaryDirectory() as temporary:
    site=Path(temporary)/'site'
    shutil.copytree(ROOT,site,ignore=shutil.ignore_patterns('.git','_site','__pycache__','content','comparisons'))
    (site/'content').mkdir()
    legacy=site/'content/2026-10-17-legacy-weekly.md'
    legacy.write_text('---\ndate: 2026-10-17\ntype: weekly\ntitle: Прежний формат\ncount: 1\ndetails: 1\nshorts: 0\n---\n# Прежний формат\n\n## Материал\n\n[Источник](https://example.com/legacy)\n\n## Что из этого применить в платформе\n\nПроверить в пилоте.\n\n## Все находки выпуска\n\n1. [Материал](https://example.com/legacy)\n')
    reader=site/'content/2026-10-18-thematic.md'
    reader.write_text(READER)
    assert run(site,'build.py').returncode==0
    valid=run(site,'check.py')
    assert valid.returncode==0,valid.stderr
    for wrong in [
        READER.replace('2. [Граница доступа](https://example.com/second)\n',''),
        READER.replace('[Граница доступа](https://example.com/second)','[Другая тема](https://example.com/second)'),
        READER.replace('## Что из этого применить в платформе','## Прочее'),
        READER.replace('2. [Граница доступа](https://example.com/second)','2. [Граница доступа](https://example.com/wrong)'),
    ]:
        reader.write_text(wrong)
        assert run(site,'build.py').returncode==0
        rejected=run(site,'check.py')
        assert rejected.returncode!=0,'Invalid thematic edition accepted'
print('PASS: thematic and legacy weekly; topics/list/source links/practice; invalid entries rejected')
