"""Only the explicitly supplied OpenAI email can be published without a public URL."""
from pathlib import Path
from html.parser import HTMLParser
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
TITLE='OpenAI удвоила лимиты Work и Codex в Pro и готовит общий бюджет использования'
SHORT_TITLE='OpenAI удвоила лимиты Work и Codex в Pro'
SUPPLEMENT_URLS=[
    'https://help.openai.com/en/articles/20001626-api-credits-benefit-for-eligible-chatgpt-subscriptions',
    'https://latent.space/p/ainews-google-admits-ai-mode-hurts-search-revenue-15-500b-drop-worst-since-2004-ipo-ai-bear-market-c/',
    'https://x.com/claudeai/status/2116220869479428500',
]
SUPPLEMENT=' · '.join('['+label+']('+url+')' for label,url in zip(['API-кредиты','Обзор Latent Space','Claude Ultra'],SUPPLEMENT_URLS))
NOTE='Источник — письмо OpenAI получателю Pro, предоставлено пользователем 1 ноября; дата отправки и публичная ссылка неизвестны.'
READER=f'''---
date: 2026-11-01
type: weekly
title: Недельный выпуск
count: 2
sections: 3
provided_source: openai-pro-email-2026-11-01
---
# Недельный выпуск

## Новости

### Публичный источник

[Источник](https://example.com/public)

#### Подробность без отдельного якоря

Дополнительный абзац.

### {TITLE}

Пользователь предоставил письмо об изменении лимитов.

{NOTE}

## Что из этого применить в платформе

Проверить условия доступа.

## Все находки выпуска

1. [Публичный источник](https://example.com/public)

2. {TITLE}. {NOTE}
'''

SHORT_READER=READER.replace('type: weekly','type: working').replace(TITLE,SHORT_TITLE).replace(NOTE+'\n\n##',NOTE+'\n\nДополнительные сведения: '+SUPPLEMENT+'\n\n##').replace('2. '+SHORT_TITLE+'. '+NOTE,'2. '+SHORT_TITLE+'. '+NOTE+' · '+SUPPLEMENT)

class FindingLinks(HTMLParser):
    def __init__(self,text):
        super().__init__();self.inside=False;self.heading=False;self.links=[];self.sources=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='article' and attrs.get('class')=='finding':self.inside=True;self.sources.append(attrs['data-source'])
        if tag=='h2' and self.inside:self.heading=True
        if tag=='a' and self.heading:self.links.append(attrs['href'])
    def handle_endtag(self,tag):
        if tag=='h2':self.heading=False
        if tag=='article':self.inside=False

def run(site,name):
    return subprocess.run([sys.executable,name],cwd=site,capture_output=True,text=True)

with tempfile.TemporaryDirectory() as temporary:
    site=Path(temporary)/'site'
    shutil.copytree(ROOT,site,ignore=shutil.ignore_patterns('.git','_site','__pycache__','content','comparisons'))
    (site/'content').mkdir()
    legacy=site/'content/2026-10-31-daily.md'
    legacy.write_text('---\ndate: 2026-10-31\ntype: daily\ntitle: Прежний выпуск\n---\n# Прежний выпуск\n\n## Новости\n\n### [Прежняя тема](https://example.com/legacy)\n\nМатериал.\n')
    assert run(site,'build.py').returncode==0
    previous=(site/'_site/2026-10-31-daily.html').read_bytes()
    reader=site/'content/2026-11-01-weekly.md'
    reader.write_text(READER)
    built=run(site,'build.py');assert built.returncode==0,built.stderr
    accepted=run(site,'check.py');assert accepted.returncode==0,accepted.stderr
    archive=FindingLinks((site/'_site/findings.html').read_text())
    assert archive.links==['https://example.com/public','2026-11-01-weekly.html#section-3','https://example.com/legacy'], 'email must remain a finding linked to its precise local topic'
    assert archive.sources==['example.com','Письмо OpenAI','example.com'], 'email must have an honest source label'
    assert NOTE in (site/'_site/findings.html').read_text(), 'archive must retain the source limitation'
    assert (site/'_site/2026-10-31-daily.html').read_bytes()==previous, 'neighboring edition changed'
    full_html=(site/'_site/2026-11-01-weekly.html').read_bytes()
    short=site/'content/2026-11-01-weekly-short.md';short.write_text(SHORT_READER)
    built=run(site,'build.py');assert built.returncode==0,built.stderr
    accepted=run(site,'check.py');assert accepted.returncode==0,accepted.stderr
    archive=FindingLinks((site/'_site/findings.html').read_text())
    assert archive.links==['https://example.com/public','2026-11-01-weekly.html#section-3','2026-11-01-weekly-short.html#section-3','https://example.com/legacy'], 'short email must use its local topic, never the API credits URL'
    assert archive.sources==['example.com','Письмо OpenAI','Письмо OpenAI','example.com']
    assert (site/'_site/2026-11-01-weekly.html').read_bytes()==full_html, 'full weekly HTML changed'
    short_invalid=[
        ('short wrong slug',SHORT_READER,'2026-11-02-weekly-short'),
        ('short wrong type',SHORT_READER.replace('type: working','type: weekly'),'2026-11-01-weekly-short'),
        ('short wrong title',SHORT_READER.replace(SHORT_TITLE,'Другой заголовок'),'2026-11-01-weekly-short'),
        ('short wrong note',SHORT_READER.replace(NOTE,'Источник — другое письмо.'),'2026-11-01-weekly-short'),
        ('short wrong marker',SHORT_READER.replace('openai-pro-email-2026-11-01','other-email'),'2026-11-01-weekly-short'),
        ('short missing marker',SHORT_READER.replace('provided_source: openai-pro-email-2026-11-01\n',''),'2026-11-01-weekly-short'),
        ('short wrong supplement URL',SHORT_READER.replace(SUPPLEMENT_URLS[0],'https://example.com/api'),'2026-11-01-weekly-short'),
        ('short supplement order',SHORT_READER.replace(SUPPLEMENT_URLS[0],'TEMP').replace(SUPPLEMENT_URLS[1],SUPPLEMENT_URLS[0]).replace('TEMP',SUPPLEMENT_URLS[1]),'2026-11-01-weekly-short'),
        ('short extra supplement',SHORT_READER.replace(SUPPLEMENT,SUPPLEMENT+' · [Ещё](https://example.com/extra)'),'2026-11-01-weekly-short'),
        ('short duplicate supplement',SHORT_READER.replace(SUPPLEMENT,SUPPLEMENT+' · [Повтор]('+SUPPLEMENT_URLS[0]+')'),'2026-11-01-weekly-short'),
        ('short missing supplement',SHORT_READER.replace(' · [Claude Ultra]('+SUPPLEMENT_URLS[2]+')',''),'2026-11-01-weekly-short'),
        ('short heading masks email',SHORT_READER.replace('### '+SHORT_TITLE,'### ['+SHORT_TITLE+']('+SUPPLEMENT_URLS[0]+')'),'2026-11-01-weekly-short'),
        ('short index masks email',SHORT_READER.replace('2. '+SHORT_TITLE+'. '+NOTE+' · '+SUPPLEMENT,'2. ['+SHORT_TITLE+']('+SUPPLEMENT_URLS[0]+') · '+SUPPLEMENT),'2026-11-01-weekly-short'),
        ('short wrong index title',SHORT_READER.replace('2. '+SHORT_TITLE,'2. Иная тема'),'2026-11-01-weekly-short'),
        ('short wrong index note',SHORT_READER.replace('2. '+SHORT_TITLE+'. '+NOTE,'2. '+SHORT_TITLE+'. Иное описание.'),'2026-11-01-weekly-short'),
        ('short extra unlinked topic',SHORT_READER.replace('count: 2','count: 3').replace('## Что из этого применить','### Без источника\n\nМатериал.\n\n## Что из этого применить')+'\n3. Без источника\n','2026-11-01-weekly-short'),
        ('short extra index',SHORT_READER+'\n3. '+SHORT_TITLE+'. '+NOTE+' · '+SUPPLEMENT+'\n','2026-11-01-weekly-short'),
    ]
    for label,raw,slug in short_invalid:
        short.unlink();short=site/'content'/(slug+'.md');short.write_text(raw)
        built=run(site,'build.py')
        checked=run(site,'check.py') if built.returncode==0 else built
        assert checked.returncode!=0,f'{label}: invalid short source accepted'
    short.unlink()
    (site/'_site/2026-11-01-weekly-short.html').unlink()
    invalid=[
        ('full extra supplement',READER.replace(NOTE+'\n\n##',NOTE+'\n\n'+SUPPLEMENT+'\n\n##'),'2026-11-01-weekly'),
        ('missing marker',READER.replace('provided_source: openai-pro-email-2026-11-01\n',''),'2026-11-01-weekly'),
        ('wrong marker',READER.replace('openai-pro-email-2026-11-01','other-email'),'2026-11-01-weekly'),
        ('wrong slug',READER,'2026-11-02-weekly'),
        ('wrong type',READER.replace('type: weekly','type: working'),'2026-11-01-weekly'),
        ('missing thematic format',READER.replace('sections: 3\n',''),'2026-11-01-weekly'),
        ('wrong title',READER.replace(TITLE,'Другая тема'),'2026-11-01-weekly'),
        ('wrong note',READER.replace(NOTE,'Источник — неизвестное письмо.'),'2026-11-01-weekly'),
        ('missing note in topic',READER.replace('\n'+NOTE+'\n','\n'),'2026-11-01-weekly'),
        ('wrong index title',READER.replace('2. '+TITLE,'2. Иная тема'),'2026-11-01-weekly'),
        ('wrong index note',READER.replace('2. '+TITLE+'. '+NOTE,'2. '+TITLE+'. Источник — письмо.'),'2026-11-01-weekly'),
        ('extra index item',READER+'\n3. '+TITLE+'. '+NOTE+'\n','2026-11-01-weekly'),
        ('unused marker',READER.replace('### '+TITLE,'### [Новый материал](https://example.com/new)').replace('2. '+TITLE+'. '+NOTE,'2. [Новый материал](https://example.com/new)'),'2026-11-01-weekly'),
        ('extra unlinked topic',READER.replace('count: 2','count: 3').replace('## Что из этого применить','### Без источника\n\nМатериал.\n\n## Что из этого применить')+'\n3. Без источника\n','2026-11-01-weekly'),
        ('duplicate email topic',READER.replace('count: 2','count: 3').replace('## Что из этого применить','### '+TITLE+'\n\n'+NOTE+'\n\n## Что из этого применить')+'\n3. '+TITLE+'. '+NOTE+'\n','2026-11-01-weekly'),
    ]
    for label,raw,slug in invalid:
        reader.unlink()
        reader=site/'content'/(slug+'.md');reader.write_text(raw)
        build=run(site,'build.py')
        checked=run(site,'check.py') if build.returncode==0 else build
        assert checked.returncode!=0, f'{label}: invalid provided source accepted'
    # Ordinary weekly editions with no marker still require public sources, and remain valid.
    reader.write_text(READER.replace('provided_source: openai-pro-email-2026-11-01\n','').replace('### '+TITLE,'### [Вторая тема](https://example.com/second)').replace('2. '+TITLE+'. '+NOTE,'2. [Вторая тема](https://example.com/second)'))
    assert run(site,'build.py').returncode==0
    ordinary=run(site,'check.py');assert ordinary.returncode==0,ordinary.stderr
print('PASS: exact full/short supplied-email contracts; local archive anchors/source; 32 invalid cases rejected; normal releases and full/neighboring HTML preserved')
