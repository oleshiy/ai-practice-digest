"""Check publication boundaries, complete lists and local navigation."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import json,re,struct
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'_site'
class Page(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True);self.links=[];self.ids=set();self.prose=False;self.items=0;self.sections=0;self.viewport=False;self.icons=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:
            assert a['id'] not in self.ids,'Duplicate anchor';self.ids.add(a['id'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])
        if tag=='link' and a.get('rel')=='icon':self.icons.append(a)
        if tag=='article' and a.get('class')=='prose':self.prose=True
        if self.prose and tag=='li':self.items+=1
        if self.prose and tag=='h2':self.sections+=1
        if tag=='meta' and a.get('name')=='viewport':self.viewport=True
    def handle_endtag(self,tag):
        if tag=='article':self.prose=False

def check():
    from build import markdown,BASE,EDITIONS,COMPARISONS
    sample='# Выпуск\n\n## Материал\n\n1. [Первый](https://example.com/one)\n\n    Первый абзац.\n\n    Второй абзац.\n\n2. [Второй](https://example.com/two)\n\n    Текст.\n\nКонечная статистика.\n'
    rendered,_=markdown(sample)
    assert rendered.count('<ol>')==1 and rendered.count('<li>')==2
    assert '<p>Первый абзац.</p><p>Второй абзац.</p></li>' in rendered
    assert rendered.endswith('<p>Конечная статистика.</p>')
    pages={p.name:Page(p.read_text()) for p in OUT.glob('*.html')}
    assert len(pages)==len(EDITIONS)+4+len(COMPARISONS)+(1 if COMPARISONS else 0)
    for name,page in pages.items():
        assert page.viewport and 'main' in page.ids,name
        assert page.icons==[{'rel':'icon','type':'image/png','sizes':f'{size}x{size}','href':BASE+f'assets/favicon-{size}.png'} for size in (16,32)],name
        for link in page.links:
            u=urlsplit(link)
            if u.scheme:
                assert u.scheme in ('https','http') and u.netloc and not u.username,link
            else:
                target=u.path or name;assert target in pages,(name,link)
                if u.fragment:assert unquote(u.fragment) in pages[target].ids,(name,link)
    for e in EDITIONS:
        page=pages[e['slug']+'.html']
        if e['type']=='daily':
            if 'sections' in e:assert page.sections==e['sections'],(e['slug'],page.sections,e['sections'])
            assert page.items==0,(e['slug'],page.items)
        else:
            if 'details' in e:
                expected=e['details']+2*(e['type']!='top30')
                assert page.sections==expected,(e['slug'],page.sections,expected)
            if e['type']!='top30' and e['count'] is not None:
                assert page.items==e['count']+e.get('shorts',0),(e['slug'],page.items,e['count'])
        raw=e['body']
        nonempty=[line for line in raw.splitlines() if line.strip()]
        assert nonempty[0].startswith('# ') and nonempty[1].startswith('## '),e['slug']
        source_links=re.findall(r'\]\((https?://[^\s)]+)\)',raw)
        assert all(u in page.links for u in source_links),e['slug']
        assert source_links and len(source_links)<=len(page.links)
        assert e['slug']+'.html' in pages['index.html'].links,e['slug']
        assert e['slug']+'.html' in pages['archive.html'].links,e['slug']
    if COMPARISONS:
        assert 'comparisons.html' in pages
        assert 'comparisons.html' not in pages['index.html'].links
        assert 'comparisons.html' not in pages['archive.html'].links
        for item in COMPARISONS:
            assert item['slug']+'.html' in pages['comparisons.html'].links,item['slug']
            assert item['slug']+'.html' not in pages['index.html'].links,item['slug']
            assert item['slug']+'.html' not in pages['archive.html'].links,item['slug']
    from archive_page import findings
    rows=findings(EDITIONS)
    assert rows and len({x['url'] for x in rows})==len(rows)
    assert (OUT/'findings.html').read_text().count('class="finding"')==len(rows)
    assert all(x['edition']+'.html' in pages for x in rows)
    forbidden=r'n8n-ai-digest|/Users/|runtime/monthly|material_id|unit_id|record_hash|github_pat_|ghp_[A-Za-z0-9]{20}|BEGIN .*PRIVATE KEY'
    for folder in [ROOT/'content',OUT]:
        for f in folder.rglob('*'):
            if f.is_file() and f.suffix!='.png':assert not re.search(forbidden,f.read_text()),f
    assert set(p.suffix for p in OUT.rglob('*') if p.is_file())<= {'.html','.css','.js','.png',''}
    for size in (16,32):
        icon=(OUT/f'assets/favicon-{size}.png').read_bytes()
        assert icon==(ROOT/f'assets/favicon-{size}.png').read_bytes()
        assert icon[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',icon[16:24])==(size,size)
    original=(ROOT/'assets/agent-faceted-original-32.png').read_bytes()
    assert original[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',original[16:24])==(32,32)
    assert original != (ROOT/'assets/favicon-32.png').read_bytes(), 'favicon-32 must use the blocky v2 source'
    css=(OUT/'assets/style.css').read_text();assert '@media(max-width:600px)' in css and 'overflow-wrap:anywhere' in css
    print('PASS: generated releases; source links, anchors, privacy and responsive metadata')
if __name__=='__main__':check()
