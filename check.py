"""Check publication boundaries, complete lists and local navigation."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import json,re
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'_site'
class Page(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True);self.links=[];self.ids=set();self.prose=False;self.items=0;self.sections=0;self.viewport=False;self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:
            assert a['id'] not in self.ids,'Duplicate anchor';self.ids.add(a['id'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])
        if tag=='article' and a.get('class')=='prose':self.prose=True
        if self.prose and tag=='li':self.items+=1
        if self.prose and tag=='h2':self.sections+=1
        if tag=='meta' and a.get('name')=='viewport':self.viewport=True
    def handle_endtag(self,tag):
        if tag=='article':self.prose=False

def check():
    from build import markdown
    sample='# Выпуск\n\n## Материал\n\n1. [Первый](https://example.com/one)\n\n    Первый абзац.\n\n    Второй абзац.\n\n2. [Второй](https://example.com/two)\n\n    Текст.\n\nКонечная статистика.\n'
    rendered,_=markdown(sample)
    assert rendered.count('<ol>')==1 and rendered.count('<li>')==2
    assert '<p>Первый абзац.</p><p>Второй абзац.</p></li>' in rendered
    assert rendered.endswith('<p>Конечная статистика.</p>')
    editions=json.loads((ROOT/'editions.json').read_text());pages={p.name:Page(p.read_text()) for p in OUT.glob('*.html')}
    assert len(pages)==len(editions)+4
    for name,page in pages.items():
        assert page.viewport and 'main' in page.ids,name
        for link in page.links:
            u=urlsplit(link)
            if u.scheme:
                assert u.scheme in ('https','http') and u.netloc and not u.username,link
            else:
                target=u.path or name;assert target in pages,(name,link)
                if u.fragment:assert unquote(u.fragment) in pages[target].ids,(name,link)
    for e in editions:
        page=pages[e['slug']+'.html'];expected=e['details']+2*(e['kind']!='top30')
        assert page.sections==expected,(e['slug'],page.sections,expected)
        if e['kind']!='top30':assert page.items==e['count']+e.get('shorts',0),(e['slug'],page.items,e['count'])
        raw=(ROOT/'content'/e['file']).read_text()
        nonempty=[line for line in raw.splitlines() if line.strip()]
        assert nonempty[0].startswith('# ') and nonempty[1].startswith('## '),e['slug']
        source_links=re.findall(r'\]\((https?://[^\s)]+)\)',raw)
        assert all(u in page.links for u in source_links),e['slug']
        assert source_links and len(source_links)<=len(page.links)
    archive=json.loads((ROOT/'content/findings.json').read_text())
    assert len(archive['findings'])==646
    assert (OUT/'findings.html').read_text().count('class="finding"')==646
    assert len({x['number'] for x in archive['findings']})==646
    forbidden=r'n8n-ai-digest|/Users/|runtime/monthly|material_id|unit_id|record_hash|github_pat_|ghp_[A-Za-z0-9]{20}|BEGIN .*PRIVATE KEY'
    for folder in [ROOT/'content',OUT]:
        for f in folder.rglob('*'):
            if f.is_file():assert not re.search(forbidden,f.read_text()),f
    assert set(p.suffix for p in OUT.rglob('*') if p.is_file())<= {'.html','.css','.js',''}
    css=(OUT/'assets/style.css').read_text();assert '@media(max-width:600px)' in css and 'overflow-wrap:anywhere' in css
    print('PASS: top30; compact20/28; archive646; source links, anchors, privacy and responsive metadata')
if __name__=='__main__':check()
