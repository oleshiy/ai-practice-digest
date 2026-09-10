"""Build a small static reading site from the approved Markdown editions."""
from pathlib import Path
import html,json,re,shutil
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'_site'
BASE='https://oleshiy.github.io/ai-practice-digest/'
EDITIONS=json.loads((ROOT/'editions.json').read_text())
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
    return '<!doctype html>\n<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+' · Практики ИИ</title><meta name="description" content="'+html.escape(description,quote=True)+'"><meta name="color-scheme" content="light"><meta property="og:type" content="article"><meta property="og:locale" content="ru_RU"><meta property="og:title" content="'+html.escape(title,quote=True)+'"><meta property="og:description" content="'+html.escape(description,quote=True)+'"><meta property="og:url" content="'+BASE+path+'"><link rel="canonical" href="'+BASE+path+'"><link rel="stylesheet" href="assets/style.css"></head><body><a class="skip" href="#main">Перейти к содержанию</a><header class="masthead"><a class="brand" href="index.html">Практики <span>ИИ</span></a><nav aria-label="Главная навигация"><a href="archive.html">Архив</a><a href="https://github.com/oleshiy/ai-practice-digest">GitHub</a></nav></header>'+body+'<footer><a href="index.html">Практики ИИ</a><p>Опыт компаний, исследования и ограничения. Пересказы со ссылками на источники.</p><a href="archive.html">Все выпуски →</a></footer></body></html>\n'

def card(e):
    return '<article class="edition"><div class="eyebrow">'+html.escape(e['label'])+' <span>10 сентября 2026</span></div><h2><a href="'+e['slug']+'.html">'+html.escape(e['title'])+'</a></h2><p>'+html.escape(e['subtitle'])+'</p><div class="edition-bottom"><span>'+str(e['count'])+' находок · '+html.escape(e['window'])+'</span><a class="read" href="'+e['slug']+'.html" aria-label="Читать: '+html.escape(e['title'],quote=True)+'">Читать <span aria-hidden="true">↗</span></a></div></article>'

def build():
    OUT.mkdir(exist_ok=True);(OUT/'assets').mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'assets/style.css',OUT/'assets/style.css')
    home='<main id="main" class="home"><div class="intro"><p class="eyebrow">Редакционные выпуски</p><h1>Что работает<br>в мире ИИ</h1><p>Реальные внедрения, полезные методы и ошибки, на которых можно учиться.</p></div><section class="editions" aria-label="Выпуски">'+''.join(card(e) for e in EDITIONS)+'</section></main>'
    (OUT/'index.html').write_text(frame('Практики ИИ','Понятные русские дайджесты о реальном опыте применения искусственного интеллекта.',home,''))
    archive='<main id="main" class="home"><div class="intro compact"><p class="eyebrow">Все выпуски</p><h1>Архив</h1><p>У каждого выпуска своё окно отбора. Находки в разных выпусках могут пересекаться.</p></div><section class="editions" aria-label="Архив выпусков">'+''.join(card(e) for e in EDITIONS)+'</section></main>'
    (OUT/'archive.html').write_text(frame('Архив','Все опубликованные выпуски «Практики ИИ».',archive,'archive.html'))
    for e in EDITIONS:
        content,toc=markdown((ROOT/'content'/e['file']).read_text())
        contents='<details open><summary>В этом выпуске</summary><ol>'+''.join('<li><a href="#'+a+'">'+html.escape(t)+'</a></li>' for a,t in toc)+'</ol></details>'
        heading=(ROOT/'content'/e['file']).read_text().splitlines()[0].removeprefix('# ')
        body='<main id="main"><header class="article-head"><h1>'+html.escape(heading)+'</h1></header><div class="read-layout"><article class="prose">'+content+'</article><aside class="toc" aria-label="Оглавление">'+contents+'</aside></div><div class="after-reading"><a href="archive.html">Другие выпуски →</a><a href="#main">К началу ↑</a></div></main>'
        (OUT/(e['slug']+'.html')).write_text(frame(e['title'],e['subtitle'],body,e['slug']+'.html'))
    (OUT/'.nojekyll').write_text('')
    (OUT/'404.html').write_text(frame('Страница не найдена','Вернитесь к выпускам.', '<main id="main" class="home"><h1>Такой страницы нет</h1><p><a href="archive.html">Открыть архив выпусков</a></p></main>','404.html'))
    print('Built',len(EDITIONS),'editions and home/archive into _site')
if __name__=='__main__':build()
