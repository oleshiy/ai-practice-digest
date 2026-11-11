"""Compact daily paragraphs remain readable topics with precise archive targets."""
from pathlib import Path
import json, shutil, subprocess, sys, tempfile
from compact import compact_outline

def test_title_sentences():
    cases=[
        ('Компания [открыла модель](https://example.com/model). Цена указана в анонсе.',
         'Компания открыла модель'),
        ('По [обзору Latent Space](https://example.com/mercor), Mercor привлекла 750 млн долларов при оценке 20 млрд: компания поставляет экспертные данные для обучения и проверки AI. Mercor сообщает о росте выручки.',
         'По обзору Latent Space, Mercor привлекла 750 млн долларов при оценке 20 млрд: компания поставляет экспертные данные для обучения и проверки AI'),
        ('Anthropic, по [разбору IPO-видео](https://example.com/amd), использовала Claude Mythos, чтобы запустить Claude на ускорителях AMD: агент написал код за три дня. Раньше требовались месяцы работы.',
         'Anthropic, по разбору IPO-видео, использовала Claude Mythos, чтобы запустить Claude на ускорителях AMD: агент написал код за три дня'),
        ('Команда [выпустила протокол 1.0](https://example.com/protocol) для **модели 5.2** за 3,1 млн долларов и [открыла документацию](https://example.com/docs). Следующее предложение не входит в название.',
         'Команда выпустила протокол 1.0 для модели 5.2 за 3,1 млн долларов и открыла документацию'),
    ]
    for paragraph,expected in cases:
        body='🔹 '+paragraph
        topic=compact_outline('# Выпуск\n\n## Новости\n\n'+body+'\n')['topics'][0]
        assert topic['title']==expected,(topic['title'],expected)
        assert topic['body']==body and topic['anchor']=='finding-1'
    assert topic['url']=='https://example.com/protocol'
    assert topic['urls']==['https://example.com/protocol','https://example.com/docs']
    print('PASS: first-sentence titles; attribution before Mercor/AMD action; versions 1.0/5.2, decimal amount, link labels; unchanged body/anchors/URLs')

test_title_sentences()
if '--titles-only' in sys.argv:raise SystemExit(0)

ROOT=Path(__file__).resolve().parent
HEADER='''---
date: 2026-11-11
type: daily
title: Компактный выпуск
format: compact
count: 3
sections: 4
toc: sections
---
'''
BODY='''# Компактный выпуск

## Что можно внедрить за две недели

### Проверить восстановление

Повторить [опыт](https://example.com/snapshot) и [проверку](https://example.com/practice-only).

🔹 Практика [проверить восстановление](https://example.com/snapshot).

Собрали главное к 11 ноября.

🔥 **Hot:**

🔹 Компания [открыла модель](https://example.com/model). Цена указана в анонсе.

➡️ **Новости:**

🔹 Команда [выпустила протокол 1.0](https://example.com/protocol) — формы и кнопки.
Продолжение того же абзаца с [документацией](https://example.com/docs).

➡️ **Обсуждения и кейсы:**

🔹 Компания [сохранила память GPU](https://example.com/snapshot). Восстановление проверили в тесте.
'''

def run(site,script):
    return subprocess.run([sys.executable,script],cwd=site,capture_output=True,text=True)

with tempfile.TemporaryDirectory() as temporary:
    site=Path(temporary)/'site'
    shutil.copytree(ROOT,site,ignore=shutil.ignore_patterns('.git','_site','__pycache__'))
    assert run(site,'build.py').returncode==0
    previous={p.name:p.read_bytes() for p in (site/'_site').glob('*.html') if p.name not in ('index.html','archive.html','findings.html')}
    source=site/'content/2026-11-11-compact-fixture.md'
    source.write_text(HEADER+BODY)
    result=run(site,'build.py');assert result.returncode==0,result.stderr
    page=(site/'_site/2026-11-11-compact-fixture.html').read_text()
    assert '<p id="finding-1">🔹 Компания <a href="https://example.com/model">открыла модель</a>. Цена указана в анонсе.</p>' in page, 'compact paragraph lost its anchor or exact wording'
    assert '<p id="finding-3">🔹 Компания' in page
    assert '<h3 id="finding-' not in page, 'compact stories became headings'
    assert 'href="#compact-section-1"' in page
    archive=(site/'_site/findings.html').read_text()
    assert 'href="2026-11-11-compact-fixture.html#finding-3"' in archive, 'archive must link to exact paragraph'
    assert 'Команда выпустила протокол 1.0 — формы и кнопки</a>' in archive, 'title must retain a dotted version and the complete first sentence'
    assert 'https://example.com/practice-only' not in archive, 'practice became a finding'
    extracted=subprocess.run([sys.executable,'-c',
        'import json,build,archive_page; print(json.dumps([x for x in archive_page.findings(build.EDITIONS) if x["edition"]=="2026-11-11-compact-fixture"]))'],
        cwd=site,capture_output=True,text=True,check=True)
    rows=json.loads(extracted.stdout)
    assert [(row['title'],row['url'],row['anchor']) for row in rows]==[
        ('Компания открыла модель','https://example.com/model','finding-1'),
        ('Команда выпустила протокол 1.0 — формы и кнопки','https://example.com/protocol','finding-2'),
        ('Компания сохранила память GPU','https://example.com/snapshot','finding-3'),
    ],'archive topic mapping differs from the reader'
    assert '[документацией](https://example.com/docs)' in rows[1]['body']
    result=run(site,'check.py');assert result.returncode==0,result.stderr
    for name,content in previous.items():assert (site/'_site'/name).read_bytes()==content,name
    for wrong in (
        HEADER.replace('count: 3','count: 4')+BODY,
        HEADER.replace('sections: 4','sections: 3')+BODY,
        HEADER.replace('format: compact','format: typo')+BODY,
        HEADER.replace('type: daily','type: weekly')+BODY,
        HEADER+BODY.replace('[открыла модель](https://example.com/model)','открыла модель'),
        HEADER+BODY.replace('https://example.com/model','https://example.com/protocol'),
    ):
        source.write_text(wrong)
        built=run(site,'build.py')
        assert built.returncode!=0 or run(site,'check.py').returncode!=0,'invalid compact metadata or source accepted'
    source.write_text(HEADER.replace('count: 3\n','')+BODY)
    result=run(site,'build.py');assert result.returncode==0,result.stderr
    assert '3 находок' in (site/'_site/index.html').read_text()
    result=run(site,'check.py');assert result.returncode==0,result.stderr
    # Heading-form section labels are also supported; practice remains excluded.
    source.write_text((HEADER+BODY).replace('🔥 **Hot:**','## 🔥 Hot').replace('➡️ **Новости:**','## ➡️ Новости').replace('➡️ **Обсуждения и кейсы:**','## ➡️ Обсуждения и кейсы'))
    result=run(site,'build.py');assert result.returncode==0,result.stderr
    result=run(site,'check.py');assert result.returncode==0,result.stderr
print('PASS: compact paragraphs, counts, section navigation, source links, exact archive targets, practice exclusion and unchanged prior pages')
