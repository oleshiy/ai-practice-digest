"""Build a small static reading site from the approved Markdown editions."""
from pathlib import Path
import html,json,re,shutil
from datetime import date
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'_site'
BASE='https://oleshiy.github.io/ai-practice-digest/'
REQUIRED={'date','type','title'}
TYPES={'daily','last10','last30','top30'}
LABELS={'daily':'Суточный выпуск','last10':'10 суток','last30':'30 суток','top30':'Топ-подборка'}
TYPE_ORDER={'daily':4,'top30':3,'last10':2,'last30':1}
def releases():
    result=[];slugs=set()
    for source in sorted((ROOT/'content').glob('*.md')):
        raw=source.read_text()
        if not raw.startswith('---\n'):raise ValueError(f'{source.name}: missing metadata')
        try:header,body=raw[4:].split('\n---\n',1)
        except ValueError:raise ValueError(f'{source.name}: invalid metadata boundary')
        body=body.lstrip('\n')
        meta={}
        for line in header.splitlines():
            key,separator,value=line.partition(': ')
            if not separator or not key or not value or key in meta:raise ValueError(f'{source.name}: invalid metadata')
            meta[key]=value
        if REQUIRED-meta.keys():raise ValueError(f'{source.name}: missing {sorted(REQUIRED-meta.keys())}')
        if meta['type'] not in TYPES:raise ValueError(f'{source.name}: invalid type')
        try:date.fromisoformat(meta['date'])
        except ValueError:raise ValueError(f'{source.name}: invalid date')
        if 'count' in meta and (not meta['count'].isdigit() or int(meta['count'])<1):raise ValueError(f'{source.name}: invalid count')
        slug=source.stem
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-[a-z0-9-]+',slug) or slug in slugs:raise ValueError(f'{source.name}: invalid or duplicate slug')
        slugs.add(slug)
        if not body.startswith('# ') or body.splitlines()[0][2:]!=meta['title']:raise ValueError(f'{source.name}: title differs from body')
        meta.update({'slug':slug,'file':source.name,'body':body,'count':int(meta['count']) if 'count' in meta else None})
        meta.setdefault('label',LABELS[meta['type']])
        meta.setdefault('subtitle','Редакционный выпуск со ссылками на источники и существенными ограничениями.')
        meta.setdefault('window',meta['date'])
        for key in ('details','shorts','sections'):
            if key in meta:
                if not meta[key].isdigit():raise ValueError(f'{source.name}: invalid {key}')
                meta[key]=int(meta[key])
        result.append(meta)
    if not result:raise ValueError('No releases')
    return sorted(result,key=lambda item:(item['date'],TYPE_ORDER[item['type']],item['slug']),reverse=True)
EDITIONS=releases()

def comparisons():
    """Return only explicitly allowlisted blind comparison readers for Pages."""
    manifest_path=ROOT/'comparisons'/'published.json'
    if not manifest_path.exists():return []
    manifest=json.loads(manifest_path.read_text())
    if set(manifest)!={'schema_version','comparisons'} or manifest['schema_version']!=1 or not isinstance(manifest['comparisons'],list) or len(manifest['comparisons'])!=1:raise ValueError('comparison manifest must allowlist exactly one A/B pair')
    result=[];seen_files=set();seen_slugs=set()
    for comparison in manifest['comparisons']:
        if set(comparison)!={'id','date','title','variants'} or not isinstance(comparison['variants'],list) or len(comparison['variants'])!=2:raise ValueError('invalid comparison entry')
        try:date.fromisoformat(comparison['date'])
        except ValueError:raise ValueError('invalid comparison date')
        labels=set()
        for variant in comparison['variants']:
            if set(variant)!={'label','file','slug'} or variant['label'] not in {'A','B'} or variant['label'] in labels:raise ValueError('invalid comparison variant')
            labels.add(variant['label'])
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-blind-[ab]\.md',variant['file']) or variant['file'] in seen_files:raise ValueError('comparison file is not uniquely allowlisted')
            if not re.fullmatch(r'comparison-\d{4}-\d{2}-\d{2}-blind-[ab]',variant['slug']) or variant['slug'] in seen_slugs:raise ValueError('invalid comparison slug')
            source=ROOT/'comparisons'/variant['file']
            if not source.is_file():raise ValueError('allowlisted comparison reader missing')
            raw=source.read_text()
            if not raw.startswith('---\n'):raise ValueError('comparison reader missing metadata')
            try:header,body=raw[4:].split('\n---\n',1)
            except ValueError:raise ValueError('comparison reader invalid metadata boundary')
            meta={}
            for line in header.splitlines():
                key,separator,value=line.partition(': ')
                if not separator or not key or not value or key in meta:raise ValueError('comparison reader invalid metadata')
                meta[key]=value
            if meta.get('date')!=comparison['date'] or not meta.get('title'):raise ValueError('comparison reader date or title invalid')
            body=body.lstrip('\n')
            if not body.startswith('# ') or body.splitlines()[0][2:]!=meta['title']:raise ValueError('comparison reader title differs from body')
            seen_files.add(variant['file']);seen_slugs.add(variant['slug'])
            result.append({**comparison,'label':variant['label'],'slug':variant['slug'],'file':variant['file'],'reader_title':meta['title'],'body':body})
    return sorted(result,key=lambda item:(item['date'],item['id'],item['label']),reverse=True)
COMPARISONS=comparisons()
TOKEN=re.compile(r'`([^`]+)`|\[([^\]]+)\]\(([^\s)]+)\)|\*\*(.+?)\*\*')
def inline(text):
    out=[];pos=0
    for m in TOKEN.finditer(text):
        out.append(html.escape(text[pos:m.start()]))
        if m.group(1) is not None:out.append('<code>'+html.escape(m.group(1))+'</code>')
        elif m.group(2) is not None:
            url=m.group(3)
            if urlsplit(url).scheme not in ('http','https'):raise ValueError('Only public HTTP links allowed in edition content')
            out.append('<a href="'+html.escape(url,quote=True)+'">'+inline(m.group(2))+'</a>')
        else:out.append('<strong>'+inline(m.group(4))+'</strong>')
        pos=m.end()
    return ''.join(out)+html.escape(text[pos:])
def markdown(text):
    """Render paragraphs and numbered entries with indented continuation paragraphs."""
    blocks=[];toc=[];lines=text.splitlines();i=0;heading=0
    while i<len(lines):
        line=lines[i]
        if not line.strip():i+=1;continue
        h=re.match(r'^(#{1,3}) (.+)',line)
        if h:
            i+=1
            if len(h[1])==1:continue
            heading+=1;anchor='section-'+str(heading);title=h[2]
            toc.append((anchor,title));blocks.append(f'<h{len(h[1])} id="{anchor}">'+inline(title)+f'</h{len(h[1])}>');continue
        li=re.match(r'^(\d+\.|-) (.+)',line)
        if li:
            tag='ul' if li[1]=='-' else 'ol';blocks.append('<'+tag+'>')
            while i<len(lines):
                match=re.match(r'^(\d+\.|-) (.+)',lines[i])
                if not match:break
                item=[match[2]];i+=1
                while i<len(lines):
                    if lines[i].startswith('    '):item.append(lines[i][4:]);i+=1
                    elif not lines[i].strip():
                        item.append('');i+=1
                    else:break
                paragraphs=re.split(r'\n\s*\n','\n'.join(item).strip())
                blocks.append('<li>'+''.join('<p>'+inline(' '.join(x.splitlines()))+'</p>' for x in paragraphs if x.strip())+'</li>')
                if i>=len(lines) or not re.match(r'^(\d+\.|-) (.+)',lines[i]):break
            blocks.append('</'+tag+'>');continue
        para=[]
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#{1,3} |\d+\. |- )',lines[i]):
            para.append(lines[i].strip());i+=1
        blocks.append('<p>'+inline(' '.join(para))+'</p>')
    return '\n'.join(blocks),toc

def frame(title,description,body,path):
    return '<!doctype html>\n<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+' · Практики ИИ</title><meta name="description" content="'+html.escape(description,quote=True)+'"><meta name="color-scheme" content="light"><meta property="og:type" content="article"><meta property="og:locale" content="ru_RU"><meta property="og:title" content="'+html.escape(title,quote=True)+'"><meta property="og:description" content="'+html.escape(description,quote=True)+'"><meta property="og:url" content="'+BASE+path+'"><link rel="canonical" href="'+BASE+path+'"><link rel="icon" type="image/png" sizes="16x16" href="'+BASE+'assets/favicon-16.png"><link rel="icon" type="image/png" sizes="32x32" href="'+BASE+'assets/favicon-32.png"><link rel="stylesheet" href="assets/style.css"><script defer src="assets/releases.js"></script></head><body><a class="skip" href="#main">Перейти к содержанию</a><header class="masthead"><a class="brand" href="index.html">Практики <span>ИИ</span></a><nav aria-label="Главная навигация"><a href="archive.html">Выпуски</a><a href="findings.html">Все находки</a><a href="https://github.com/oleshiy/ai-practice-digest">GitHub</a></nav></header>'+body+'<footer><a href="index.html">Практики ИИ</a><p>Опыт компаний, исследования и ограничения. Пересказы со ссылками на источники.</p><a href="archive.html">Все выпуски →</a></footer></body></html>\n'

def card(e):
    summary=(str(e['count'])+' находок · ' if e['count'] is not None else '')+html.escape(e['window'])
    return '<article class="edition" data-release><div class="eyebrow">'+html.escape(e['label'])+' <span>'+html.escape(e['date'])+'</span></div><h2><a href="'+e['slug']+'.html">'+html.escape(e['title'])+'</a></h2><p>'+html.escape(e['subtitle'])+'</p><div class="edition-bottom"><span>'+summary+'</span><a class="read" href="'+e['slug']+'.html" aria-label="Читать: '+html.escape(e['title'],quote=True)+'">Читать <span aria-hidden="true">↗</span></a></div></article>'

def build():
    OUT.mkdir(exist_ok=True);(OUT/'assets').mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'assets/style.css',OUT/'assets/style.css')
    shutil.copyfile(ROOT/'assets/findings.js',OUT/'assets/findings.js')
    shutil.copyfile(ROOT/'assets/releases.js',OUT/'assets/releases.js')
    shutil.copyfile(ROOT/'assets/favicon-32.png',OUT/'assets/favicon-32.png')
    shutil.copyfile(ROOT/'assets/favicon-16.png',OUT/'assets/favicon-16.png')
    from archive_page import render_archive
    (OUT/'findings.html').write_text(frame('Архив находок','Поиск по принятым материалам о практиках ИИ.',render_archive(ROOT,inline),'findings.html'))
    cards=''.join(card(e) for e in EDITIONS)
    home='<main id="main" class="home"><div class="intro"><p class="eyebrow">Редакционные выпуски</p><h1>Что работает<br>в мире ИИ</h1><p>Реальные внедрения, полезные методы и ошибки, на которых можно учиться.</p></div><section class="editions" aria-label="Выпуски" data-release-list data-initial="5">'+cards+'</section><div class="release-actions"><button type="button" data-show-more hidden>Показать ещё</button><a class="read" href="archive.html">Все выпуски →</a></div></main>'
    (OUT/'index.html').write_text(frame('Практики ИИ','Понятные русские дайджесты о реальном опыте применения искусственного интеллекта.',home,''))
    archive='<main id="main" class="home"><div class="intro compact"><p class="eyebrow">Все выпуски</p><h1>Архив выпусков</h1><p>У каждого выпуска своё окно отбора. Находки в разных выпусках могут пересекаться. Остальное полезное — в <a href="findings.html">архиве с поиском</a>.</p></div><section class="editions" aria-label="Архив выпусков">'+cards+'</section></main>'
    (OUT/'archive.html').write_text(frame('Архив','Все опубликованные выпуски «Практики ИИ».',archive,'archive.html'))
    for e in EDITIONS:
        content,toc=markdown(e['body'])
        contents='<details open><summary>В этом выпуске</summary><ol>'+''.join('<li><a href="#'+a+'">'+html.escape(t)+'</a></li>' for a,t in toc)+'</ol></details>'
        heading=e['title']
        body='<main id="main"><header class="article-head"><h1>'+html.escape(heading)+'</h1></header><div class="read-layout"><article class="prose">'+content+'</article><aside class="toc" aria-label="Оглавление">'+contents+'</aside></div><div class="after-reading"><a href="archive.html">Другие выпуски →</a><a href="#main">К началу ↑</a></div></main>'
        (OUT/(e['slug']+'.html')).write_text(frame(e['title'],e['subtitle'],body,e['slug']+'.html'))
    if COMPARISONS:
        rows=[]
        for item in COMPARISONS:
            content,toc=markdown(item['body'])
            contents='<details open><summary>В этом варианте</summary><ol>'+''.join('<li><a href="#'+a+'">'+html.escape(t)+'</a></li>' for a,t in toc)+'</ol></details>'
            body='<main id="main"><header class="article-head"><p class="eyebrow">'+html.escape(item['title'])+' · вариант '+item['label']+'</p><h1>'+html.escape(item['reader_title'])+'</h1></header><div class="read-layout"><article class="prose">'+content+'</article><aside class="toc" aria-label="Оглавление">'+contents+'</aside></div><div class="after-reading"><a href="comparisons.html">Все варианты сравнения →</a><a href="#main">К началу ↑</a></div></main>'
            (OUT/(item['slug']+'.html')).write_text(frame(item['reader_title'],'Слепой вариант для сравнения редакционных решений.',body,item['slug']+'.html'))
            rows.append('<article class="edition"><div class="eyebrow">Слепое сравнение <span>'+html.escape(item['date'])+'</span></div><h2><a href="'+item['slug']+'.html">Вариант '+item['label']+'</a></h2><p>'+html.escape(item['reader_title'])+'</p><div class="edition-bottom"><span>Не является обычным выпуском</span><a class="read" href="'+item['slug']+'.html">Читать <span aria-hidden="true">↗</span></a></div></article>')
        comparison_index='<main id="main" class="home"><div class="intro compact"><p class="eyebrow">Сравнение вариантов</p><h1>Слепое A/B-сравнение</h1><p>'+html.escape(COMPARISONS[0]['title'])+'. Два варианта показываются отдельно для выбора; они не добавлены в обычную ленту выпусков.</p></div><section class="editions" aria-label="Варианты сравнения">'+''.join(rows)+'</section></main>'
        (OUT/'comparisons.html').write_text(frame('Сравнение вариантов','Два слепых варианта редакционного выпуска для выбора.',comparison_index,'comparisons.html'))
    (OUT/'.nojekyll').write_text('')
    (OUT/'404.html').write_text(frame('Страница не найдена','Вернитесь к выпускам.', '<main id="main" class="home"><h1>Такой страницы нет</h1><p><a href="archive.html">Открыть архив выпусков</a></p></main>','404.html'))
    print('Built',len(EDITIONS),'editions and home/archive into _site')
if __name__=='__main__':build()
