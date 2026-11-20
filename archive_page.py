"""Build the searchable archive of findings from the published editions themselves.

Every story H3 in an edition is one finding (title, source link, the paragraphs under it); one-line
entries in «Остальное» count too. Approved reference sidecars retain useful summaries outside
editions, including separately addressed practices whose source URLs may overlap.
With opt-in section navigation, H3 groups in the practical section are not findings.
"""
import html,json,re
from pathlib import Path
from datetime import date,timedelta
from urllib.parse import urlsplit
from provided_source import provided_topic,SOURCE
from compact import compact_outline

LINK=re.compile(r'\[([^\]]+)\]\((https?://[^\s)]+)\)')
FRESH_DAYS=7

def findings(editions):
    """Newest edition first; a URL seen in several editions keeps its newest appearance."""
    seen=set();rows=[]
    for e in editions:
        if e.get('format')=='compact':
            for topic in compact_outline(e['body'])['topics']:
                url=topic['url']
                if url in seen:continue
                seen.add(url)
                rows.append({'title':topic['title'],'url':url,'source':urlsplit(url).netloc.removeprefix('www.'),'date':e['date'],
                             'edition':e['slug'],'edition_title':e['title'],'section':topic['section'],'body':topic['body'],
                             'anchor':topic['anchor']})
            continue
        section='';lines=e['body'].splitlines();i=0;anchor=0
        while i<len(lines):
            line=lines[i]
            if re.match(r'^#{2,3} ',line):
                anchor+=1
                while anchor in e.get('reserved_heading_ids',()):anchor+=1
            if line.startswith('## '):section=line[3:].strip();i+=1;continue
            if e.get('toc')=='sections' and section in ('Что из этого применить в платформе', 'Что можно внедрить за две недели'):i+=1;continue
            title=url=None;body=[];provided=False
            if line.startswith('### '):
                heading=line[4:].strip();m=LINK.fullmatch(heading)
                if m:title,url=m.group(1),m.group(2)
                else:title=heading
                i+=1
                while i<len(lines) and not re.match(r'^#{1,3} ',lines[i]):
                    if lines[i].startswith(('![','Подпись: ')):i+=1;continue
                    if lines[i].strip():body.append(lines[i][5:].strip() if lines[i].startswith('#### ') else lines[i].strip())
                    i+=1
                if url is None:
                    if provided_topic(e,title,body):
                        url=e['slug']+'.html#section-'+str(anchor);provided=True
                    else:
                        found=LINK.search(' '.join(body));url=found.group(2) if found else None
                body=[b for b in body if not (b.startswith('[') and LINK.fullmatch(b.split(' · ')[0]) and len(b)<120)]
            elif section=='Остальное' and LINK.match(line):
                m=LINK.match(line);title,url=m.group(1),m.group(2);body=[line[m.end():].strip(' —-–.')];i+=1
            else:i+=1;continue
            if not url or url in seen:continue
            seen.add(url)
            rows.append({'title':title,'url':url,'source':SOURCE if provided else urlsplit(url).netloc.removeprefix('www.'),'date':e['date'],
                         'edition':e['slug'],'edition_title':e['title'],'section':section,'body':' '.join(body)})
    return rows

def reference_findings(folder=None):
    """Read explicitly archived summaries, independently of edition URL deduplication."""
    folder=Path(folder) if folder is not None else Path(__file__).resolve().parent/'findings'
    rows=[];seen=set()
    for path in sorted(folder.glob('*.json')):
        data=json.loads(path.read_text())
        if not isinstance(data,dict) or set(data)!={'date','window','items'}:raise ValueError('invalid reference archive envelope')
        try:date.fromisoformat(data['date'])
        except (TypeError,ValueError):raise ValueError('invalid reference date')
        if path.name!=data['date']+'-reference.json':raise ValueError('reference filename must match date')
        if not isinstance(data['window'],str) or not data['window'].strip() or '\n' in data['window']:raise ValueError('reference publication window required')
        if not isinstance(data['items'],list) or not data['items']:raise ValueError('reference items required')
        for item in data['items']:
            if not isinstance(item,dict) or set(item)!={'id','kind','title','url','body'}:raise ValueError('invalid reference item')
            if any(not isinstance(v,str) or not v.strip() for v in item.values()):raise ValueError('empty reference field')
            if item['kind'] not in ('topic','practice'):raise ValueError('invalid reference kind')
            if not re.fullmatch('reference-'+re.escape(data['date'])+'-'+item['kind']+'-[1-9][0-9]*',item['id']) or item['id'] in seen:raise ValueError('invalid or duplicate reference id')
            url=urlsplit(item['url'])
            if url.scheme not in ('http','https') or not url.netloc or url.username or any(c.isspace() for c in item['url']):raise ValueError('reference source must be public HTTP URL')
            seen.add(item['id'])
            rows.append({**item,'source':url.netloc.removeprefix('www.'),'date':data['date'],'window':data['window'],'view':'reference'})
    return rows


def render_archive(editions, inline, reference_rows=None):
    rows=[{**row,'view':'edition'} for row in findings(editions)]
    references=[] if reference_rows is None else reference_rows
    rows.extend(references)
    rows.sort(key=lambda row:row['date'],reverse=True)
    newest=max(date.fromisoformat(row['date']) for row in rows);cutoff=newest-timedelta(days=FRESH_DAYS)
    hosts=sorted({x['source'] for x in rows})
    options=''.join('<option value="'+html.escape(x,quote=True)+'">'+html.escape(x)+'</option>' for x in hosts)
    cards=[]
    for n,x in enumerate(rows):
        fresh=date.fromisoformat(x['date'])>=cutoff
        hidden=' hidden' if n>=20 else ''
        if x['view']=='reference':
            label='Адресная практика' if x['kind']=='practice' else 'Тема'
            note=('<p class="finding-meta">Справочный архив · '+label+' · Дата подборки: '+html.escape(x['date'])+'</p>'
                  '<p class="finding-meta">Окно исходных публикаций: '+html.escape(x['window'])+'</p>')
            anchor=' id="'+html.escape(x['id'],quote=True)+'"'
        else:
            target=x['edition']+'.html'+('#'+x['anchor'] if x.get('anchor') else '')
            note=('<p class="finding-meta">'+html.escape(x['date'])+' · <a href="'+target+'">'+html.escape(x['section'] or 'выпуск')+'</a></p>')
            anchor=''
        cards.append('<article class="finding" data-source="'+html.escape(x['source'],quote=True)+'" data-fresh="'+str(fresh).lower()+'" data-view="'+x['view']+'" data-date="'+x['date']+'"'+anchor+hidden+'><h2><a href="'+html.escape(x['url'],quote=True)+'">'+html.escape(x['title'])+'</a></h2>'+note+('<p>'+inline(x['body'])+'</p>' if x['body'] else '')+'</article>')
    first=min(row['date'] for row in rows)
    source_note=' Для письма без публичной ссылки доступен разбор с описанием источника.' if any(x['source']==SOURCE for x in rows) else ''
    return ('<style>@media(min-width:851px){.findings-page .filters{grid-template-columns:repeat(3,minmax(0,1fr))}}</style><main id="main" class="findings-page"><header class="archive-head"><h1>Архив находок</h1><p>'+str(len(rows))+' находок из выпусков и справочного архива с '+html.escape(first)+' по '+html.escape(newest.isoformat())+'. Даты обозначают выпуск или подборку, а не дату исходной публикации. Справочные темы и адресные практики сохранены отдельно от выпуска; их наличие здесь не означает рекомендацию для платформы.'+source_note+'</p></header>'
            '<form class="filters" onsubmit="return false"><label>Поиск по названию и тексту<input id="finding-search" type="search" placeholder="Например: проверка кода" autocomplete="off"></label><label>Раздел<select id="finding-view"><option value="">Всё</option><option value="edition">В выпусках</option><option value="reference">Справочный архив</option></select></label><label>Дата выпуска / подборки<input id="finding-date" type="date"></label><label>Период<select id="finding-period"><option value="last30">За всё время</option><option value="last10">Последние '+str(FRESH_DAYS)+' дней</option></select></label><label>Источник<select id="finding-source"><option value="">Все источники</option>'+options+'</select></label><button id="finding-clear" type="button">Сбросить</button></form>'
            '<div class="pager"><p id="finding-count" role="status" aria-live="polite">'+str(len(rows))+' находок</p><div><button id="finding-previous" type="button" disabled>← Назад</button><button id="finding-next" type="button">Далее →</button></div></div>'
            '<noscript><p>Для поиска и фильтров включите JavaScript. Без него ниже доступны все находки; можно использовать поиск браузера.</p><style>.filters,.pager{display:none}.finding[hidden]{display:block}</style></noscript>'
            '<section data-findings aria-label="Найденные материалы">'+''.join(cards)+'</section></main><script src="assets/findings.js" defer></script>')
