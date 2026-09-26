"""Build the searchable archive of findings from the published editions themselves.

Every H3 in an edition is one finding (title, source link, the paragraphs under it); one-line
entries in «Остальное» count too. Nothing is stored separately: the archive is derived at build
time, so a new edition appears here on the next Pages build without any extra step.
"""
import html,re
from datetime import date,timedelta
from urllib.parse import urlsplit

LINK=re.compile(r'\[([^\]]+)\]\((https?://[^\s)]+)\)')
FRESH_DAYS=7

def findings(editions):
    """Newest edition first; a URL seen in several editions keeps its newest appearance."""
    seen=set();rows=[]
    for e in editions:
        section='';lines=e['body'].splitlines();i=0
        while i<len(lines):
            line=lines[i]
            if line.startswith('## '):section=line[3:].strip();i+=1;continue
            title=url=None;body=[]
            if line.startswith('### '):
                heading=line[4:].strip();m=LINK.fullmatch(heading)
                if m:title,url=m.group(1),m.group(2)
                else:title=heading
                i+=1
                while i<len(lines) and not lines[i].startswith('#'):
                    if lines[i].strip():body.append(lines[i].strip())
                    i+=1
                if url is None:
                    found=LINK.search(' '.join(body));url=found.group(2) if found else None
                body=[b for b in body if not (b.startswith('[') and LINK.fullmatch(b.split(' · ')[0]) and len(b)<120)]
            elif section=='Остальное' and LINK.match(line):
                m=LINK.match(line);title,url=m.group(1),m.group(2);body=[line[m.end():].strip(' —-–.')];i+=1
            else:i+=1;continue
            if not url or url in seen:continue
            seen.add(url)
            rows.append({'title':title,'url':url,'source':urlsplit(url).netloc.removeprefix('www.'),'date':e['date'],
                         'edition':e['slug'],'edition_title':e['title'],'section':section,'body':' '.join(body)})
    return rows

def render_archive(editions, inline):
    rows=findings(editions)
    newest=max(date.fromisoformat(e['date']) for e in editions);cutoff=newest-timedelta(days=FRESH_DAYS)
    hosts=sorted({x['source'] for x in rows})
    options=''.join('<option value="'+html.escape(x,quote=True)+'">'+html.escape(x)+'</option>' for x in hosts)
    cards=[]
    for n,x in enumerate(rows):
        fresh=date.fromisoformat(x['date'])>=cutoff
        hidden=' hidden' if n>=20 else ''
        note=('<p class="finding-meta">'+html.escape(x['date'])+' · <a href="'+x['edition']+'.html">'+html.escape(x['section'] or 'выпуск')+'</a></p>')
        cards.append('<article class="finding" data-source="'+html.escape(x['source'],quote=True)+'" data-fresh="'+str(fresh).lower()+'"'+hidden+'><h2><a href="'+html.escape(x['url'],quote=True)+'">'+html.escape(x['title'])+'</a></h2>'+note+('<p>'+inline(x['body'])+'</p>' if x['body'] else '')+'</article>')
    first=min(e['date'] for e in editions)
    return ('<main id="main" class="findings-page"><header class="archive-head"><h1>Архив находок</h1><p>'+str(len(rows))+' находок из всех выпусков с '+html.escape(first)+' по '+html.escape(newest.isoformat())+'. Архив собирается из самих выпусков при каждой публикации: каждая находка ведёт на источник и на выпуск, где она разобрана.</p></header>'
            '<form class="filters" onsubmit="return false"><label>Поиск по названию и тексту<input id="finding-search" type="search" placeholder="Например: проверка кода" autocomplete="off"></label><label>Период<select id="finding-period"><option value="last30">Все выпуски</option><option value="last10">Последние '+str(FRESH_DAYS)+' дней</option></select></label><label>Источник<select id="finding-source"><option value="">Все источники</option>'+options+'</select></label><button id="finding-clear" type="button">Сбросить</button></form>'
            '<div class="pager"><p id="finding-count" role="status" aria-live="polite">'+str(len(rows))+' находок</p><div><button id="finding-previous" type="button" disabled>← Назад</button><button id="finding-next" type="button">Далее →</button></div></div>'
            '<noscript><p>Для поиска и фильтров включите JavaScript. Без него ниже доступны все находки; можно использовать поиск браузера.</p><style>.filters,.pager{display:none}.finding[hidden]{display:block}</style></noscript>'
            '<section data-findings aria-label="Найденные материалы">'+''.join(cards)+'</section></main><script src="assets/findings.js" defer></script>')
