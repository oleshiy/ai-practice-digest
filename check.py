"""Check publication boundaries, complete lists and local navigation."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import json,re,struct
from provided_source import provided_source,provided_topic,NOTE
from compact import compact_outline
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'_site'
class Page(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True);self.links=[];self.ids=set();self.prose=False;self.items=0;self.sections=0;self.viewport=False;self.icons=[];self.images=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:
            assert a['id'] not in self.ids,'Duplicate anchor';self.ids.add(a['id'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])
        if tag=='link' and a.get('rel')=='icon':self.icons.append(a)
        if tag=='img':self.images.append(a)
        if tag=='article' and a.get('class')=='prose':self.prose=True
        if self.prose and tag=='li':self.items+=1
        if self.prose and tag=='h2':self.sections+=1
        if tag=='meta' and a.get('name')=='viewport':self.viewport=True
    def handle_endtag(self,tag):
        if tag=='article':self.prose=False

def check_thematic(edition,page):
    """Thematic weeks use H3 scenarios, a practical section and one complete source list."""
    raw=edition['body'];practice='## Что из этого применить в платформе';complete='## Все находки выпуска'
    assert raw.count(practice)==1 and raw.count(complete)==1, 'thematic practice and source list required'
    topics,tail=raw.split(practice,1)
    practice_body,listed=tail.split(complete,1)
    assert practice_body.strip(), 'thematic practice is empty'
    expected=[];provided_count=0
    allowed=provided_source(edition)
    for fragment in re.split(r'(?m)(?=^### )',topics):
        if not fragment.startswith('### '):continue
        fragment=fragment.split('\n## ',1)[0]
        heading=fragment.splitlines()[0][4:]
        title=re.sub(r'\[([^]]+)\]\([^)]+\)',r'\1',heading)
        fragment='\n'.join(line for line in fragment.splitlines() if not line.startswith(('![','Подпись: ')))
        urls=list(dict.fromkeys(re.findall(r'\]\((https?://[^\s)]+)\)',fragment)))
        if allowed and title==allowed['title']:
            assert heading==title and provided_topic(edition,title,fragment.splitlines()), ('provided topic differs from allowlist',title)
            provided_count+=1
        else:assert urls, ('thematic topic has no source',title)
        expected.append((title,urls))
    assert provided_count==int(bool(allowed)), 'provided source must identify exactly one topic'
    actual=[];provided_index_count=0
    for line in listed.splitlines():
        if not re.match(r'^\d+\. ',line):continue
        links=re.findall(r'\[([^]]+)\]\((https?://[^\s)]+)\)',line)
        if allowed and re.match(r'\d+\. '+re.escape(allowed['title']+'. '+NOTE),line):
            suffix=r'(?: · \[[^\]\n]+\]\(https?://[^\s)]+\))'+('{'+str(len(allowed['urls']))+'}')
            assert re.fullmatch(r'\d+\. '+re.escape(allowed['title']+'. '+NOTE)+suffix,line), 'provided index must keep plain title and exact source note'
            assert [url for _,url in links]==allowed['urls'], 'provided index supplementary sources differ'
            actual.append((allowed['title'],allowed['urls']));provided_index_count+=1
        else:
            assert links, 'thematic list entry has no source'
            actual.append((links[0][0],[url for _,url in links]))
    assert provided_index_count==int(bool(allowed)), 'provided index must identify exactly one topic'
    assert expected==actual, ('thematic source list differs from topics',edition['slug'])
    assert len({title for title,_ in expected})==len(expected), 'thematic duplicate topic'
    assert len(expected)==edition['count'], 'thematic topic count differs'
    assert page.sections==edition['sections'], 'thematic section count differs'
    if 'details' in edition and 'shorts' in edition:
        assert edition['details']+edition['shorts']==edition['count'], 'thematic depth counts differ'

def check():
    from build import markdown,BASE,EDITIONS,COMPARISONS,FIGURE,figure_asset
    sample='# Выпуск\n\n## Материал\n\n1. [Первый](https://example.com/one)\n\n    Первый абзац.\n\n    Второй абзац.\n\n2. [Второй](https://example.com/two)\n\n    Текст.\n\nКонечная статистика.\n'
    rendered,_=markdown(sample)
    assert rendered.count('<ol>')==1 and rendered.count('<li>')==2
    assert '<p>Первый абзац.</p><p>Второй абзац.</p></li>' in rendered
    assert rendered.endswith('<p>Конечная статистика.</p>')
    pages={p.name:Page(p.read_text()) for p in OUT.glob('*.html')}
    assert len(pages)==len(EDITIONS)+sum(bool(e.get('redirect_from')) for e in EDITIONS)+4+len(COMPARISONS)+(1 if COMPARISONS else 0)
    for name,page in pages.items():
        assert page.viewport and 'main' in page.ids,name
        assert page.icons==[{'rel':'icon','type':'image/png','sizes':f'{size}x{size}','href':BASE+f'assets/favicon-{size}.png'} for size in (16,32)],name
        for image in page.images:
            src=image.get('src','')
            assert FIGURE.fullmatch('![image]('+src+')') and image.get('alt'),(name,image)
            original=figure_asset(src);assert (OUT/src).read_bytes()==original.read_bytes(),(name,src)
        for link in page.links:
            u=urlsplit(link)
            if u.scheme:
                assert u.scheme in ('https','http') and u.netloc and not u.username,link
            else:
                if FIGURE.fullmatch('![image]('+link+')'):
                    assert (OUT/link).is_file(),(name,link)
                    continue
                target=u.path or name;assert target in pages,(name,link)
                if u.fragment:assert unquote(u.fragment) in pages[target].ids,(name,link)
    for e in EDITIONS:
        provided_source(e)
        page=pages[e['slug']+'.html']
        if e.get('format')=='compact':
            outline=compact_outline(e['body']);topics=outline['topics']
            assert topics and len(topics)==e['count'],(e['slug'],'compact topic count differs')
            assert len({topic['url'] for topic in topics})==len(topics),(e['slug'],'duplicate compact source')
            assert all(topic['anchor'] in page.ids for topic in topics),(e['slug'],'compact anchor missing')
            if 'sections' in e:assert len(outline['sections'])==e['sections'],(e['slug'],'compact section count differs')
            assert page.items==0,(e['slug'],page.items)
        elif e['type']=='daily':
            if 'sections' in e:assert page.sections==e['sections'],(e['slug'],page.sections,e['sections'])
            assert page.items==0,(e['slug'],page.items)
        elif 'sections' in e:
            check_thematic(e,page)
        else:
            if 'details' in e:
                expected=e['details']+2*(e['type']!='top30')
                assert page.sections==expected,(e['slug'],page.sections,expected)
            if e['type']!='top30' and e['count'] is not None:
                assert page.items==e['count']+e.get('shorts',0),(e['slug'],page.items,e['count'])
        raw=e['body']
        nonempty=[line for line in raw.splitlines() if line.strip()]
        assert nonempty[0].startswith('# ') and (e.get('format')=='compact' or nonempty[1].startswith('## ') or e['type']!='daily' and 'sections' in e and nonempty[1].startswith('### ')),e['slug']
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
