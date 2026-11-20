"""Standalone reference text survives URL overlap without becoming a release."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from html.parser import HTMLParser
import archive_page
from build import inline

class Cards(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.cards=[]; self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='article' and a.get('class')=='finding': self.cards.append(a)

def run():
    assert hasattr(archive_page, 'reference_findings'), 'reference sidecar loader missing'
    data={'date':'2026-11-18','window':'5–18 ноября 2026, Europe/Moscow','items':[
        {'id':'reference-2026-11-18-topic-1','kind':'topic','title':'Справочная тема','url':'https://example.com/a','body':'Точный [текст](https://example.com/a) темы.'},
        {'id':'reference-2026-11-18-practice-1','kind':'practice','title':'Адресная практика','url':'https://example.com/a','body':'Отдельный текст практики.'}]}
    editions=[{'date':'2026-11-18','slug':'2026-11-18-daily','title':'Выпуск','format':'compact','body':'# Выпуск\n\n## Новости\n\n🔹 [Событие](https://example.com/a). Факт.\n'}]
    with TemporaryDirectory() as temp:
        folder=Path(temp); path=folder/'2026-11-18-reference.json'
        path.write_text(json.dumps(data))
        rows=archive_page.reference_findings(folder)
        assert [r['body'] for r in rows]==[i['body'] for i in data['items']]
        page=archive_page.render_archive(editions,inline,reference_rows=rows)
        cards=Cards(page).cards
        assert len(cards)==3, 'URL overlap must preserve edition, reference topic and practice'
        assert [c.get('data-view') for c in cards].count('reference')==2
        assert all(c['data-date']=='2026-11-18' for c in cards)
        assert {c.get('id') for c in cards if c.get('data-view')=='reference'}=={i['id'] for i in data['items']}
        assert 'Отдельный текст практики.' in page and data['window'] in page
        assert archive_page.findings(editions)==archive_page.findings(deepcopy(editions)), 'references must not mutate editions'
        for mutate in [lambda d:d['items'].append(d['items'][0]),lambda d:d['items'][0].update(url='javascript:alert(1)'),lambda d:d['items'][0].update(id='bad id'),lambda d:d.update(date='2026-02-30'),lambda d:d['items'][0].update(kind='daily')]:
            bad=deepcopy(data);mutate(bad);path.write_text(json.dumps(bad))
            try:archive_page.reference_findings(folder)
            except ValueError:pass
            else:raise AssertionError('invalid sidecar accepted')
    print('PASS: reference archive preserves overlapping texts, dates and anchors; rejects invalid input')

if __name__=='__main__':run()
