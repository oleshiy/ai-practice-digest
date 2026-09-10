"""Build the searchable archive from the previous approved editorial copy."""
import html,json
from pathlib import Path

def render_archive(root, inline):
    data=json.loads((root/'content/findings.json').read_text());rows=data['findings'];assert len(rows)==data['count']==646
    hosts=sorted({x['source'] for x in rows})
    options=''.join('<option value="'+html.escape(x,quote=True)+'">'+html.escape(x)+'</option>' for x in hosts)
    cards=[]
    for n,x in enumerate(rows):
        hidden=' hidden' if n>=20 else ''
        cards.append('<article class="finding" data-source="'+html.escape(x['source'],quote=True)+'" data-fresh="'+str(x['fresh']).lower()+'"'+hidden+'><h2><a href="'+html.escape(x['url'],quote=True)+'">'+html.escape(x['title'])+'</a></h2><p>'+inline(x['body_markdown'])+'</p></article>')
    return '<main id="main" class="findings-page"><header class="archive-head"><h1>Архив находок</h1><p>646 принятых находок за 11 августа — 10 сентября 2026. Здесь сохранены прежние принятые пересказы; более понятная редакция готовится и будет появляться после проверки. Компактные дайджесты доступны в <a href="archive.html">архиве выпусков</a>.</p><p class="archive-window">Окно — с 11 августа 2026, 00:27:44, до 10 сентября 2026, 00:27:44 МСК, без правой границы. Время показано до секунды. Фильтр последних 10 суток отбирает по дате основного источника и начинается 31 августа в то же время.</p></header><form class="filters" onsubmit="return false"><label>Поиск по названию и тексту<input id="finding-search" type="search" placeholder="Например: проверка кода" autocomplete="off"></label><label>Период<select id="finding-period"><option value="last30">Все 30 суток</option><option value="last10">Основной источник за 10 суток</option></select></label><label>Источник<select id="finding-source"><option value="">Все источники</option>'+options+'</select></label><button id="finding-clear" type="button">Сбросить</button></form><div class="pager"><p id="finding-count" role="status" aria-live="polite">646 находок</p><div><button id="finding-previous" type="button" disabled>← Назад</button><button id="finding-next" type="button">Далее →</button></div></div><noscript><p>Для поиска и фильтров включите JavaScript. Без него ниже доступны все находки; можно использовать поиск браузера.</p><style>.filters,.pager{display:none}.finding[hidden]{display:block}</style></noscript><section data-findings aria-label="Найденные материалы">'+''.join(cards)+'</section></main><script src="assets/findings.js" defer></script>'
