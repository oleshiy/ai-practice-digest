"""Opt-in navigation keeps topic links ahead of the article in reading order."""
from pathlib import Path
from html.parser import HTMLParser
import shutil
import subprocess
import sys
import tempfile


class ReaderOrder(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.order=[]
        self.links=[]
        self.headings=[]
        self.toc_labels=[]
        self.in_toc_link=False
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attributes=dict(attributes)
        if tag in ('article','aside'):
            self.order.append(tag)
        if tag=='a' and attributes.get('href','').startswith('#section-'):
            self.links.append(attributes['href'][1:])
            self.in_toc_link=True
        if tag in ('h2','h3'):
            self.headings.append(attributes.get('id'))

    def handle_endtag(self, tag):
        if tag=='a':self.in_toc_link=False

    def handle_data(self, text):
        if self.in_toc_link:self.toc_labels.append(text)


class ArchiveFindings(HTMLParser):
    def __init__(self,text):
        super().__init__();self.in_finding=False;self.in_heading=False;self.urls=[];self.feed(text)

    def handle_starttag(self,tag,attributes):
        attributes=dict(attributes)
        if tag=='article' and attributes.get('class')=='finding':self.in_finding=True
        if tag=='h2' and self.in_finding:self.in_heading=True
        if tag=='a' and self.in_heading:self.urls.append(attributes['href'])

    def handle_endtag(self,tag):
        if tag=='h2':self.in_heading=False
        if tag=='article':self.in_finding=False


def build(checkout):
    result=subprocess.run([sys.executable,'build.py'],cwd=checkout,capture_output=True,text=True)
    assert result.returncode==0, result.stderr


original=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as temp:
    checkout=Path(temp)/'site'
    shutil.copytree(original,checkout,ignore=shutil.ignore_patterns('.git','_site','__pycache__'))
    build(checkout)
    prior={p.stem:(checkout/'_site'/(p.stem+'.html')).read_bytes() for p in (checkout/'content').glob('*.md')}
    source=checkout/'content'/'2026-10-10-navigation-fixture.md'
    header='---\ndate: 2026-10-10\ntype: daily\ntitle: Проверка навигации\n'
    body='---\n# Проверка навигации\n\n## Первая тема\n\nМатериал.\n\n### Вторая тема\n\n[Источник](https://example.com/source)\n'
    source.write_text(header+body)
    build(checkout)
    output=checkout/'_site'/'2026-10-10-navigation-fixture.html'
    assert ReaderOrder(output.read_text()).order==['article','aside'], 'default reader order changed'
    source.write_text(header+'navigation: top\n'+body)
    build(checkout)
    reader=ReaderOrder(output.read_text())
    assert reader.order==['aside','article'], 'opt-in navigation must precede article for keyboard and screen readers'
    assert reader.links==reader.headings==['section-1','section-2'], 'navigation must retain all section targets'
    for slug,content in prior.items():
        assert (checkout/'_site'/(slug+'.html')).read_bytes()==content, f'prior edition changed: {slug}'
    linked_body=body+'\n### [Третья `тема` и **пример**](https://example.com/long-source-url)\n\nМатериал.\n'
    source.write_text(header+'navigation: top\ntoc: plain\n'+linked_body)
    build(checkout)
    rendered=output.read_text()
    reader=ReaderOrder(rendered)
    assert reader.links==reader.headings==['section-1','section-2','section-3'], 'linked heading must retain its anchor'
    assert reader.toc_labels==['Первая тема','Вторая тема','Третья тема и пример'], 'TOC must contain labels, without raw Markdown or source URLs'
    assert '<h3 id="section-3"><a href="https://example.com/long-source-url">' in rendered, 'source link must remain in article heading'
    for slug,content in prior.items():
        assert (checkout/'_site'/(slug+'.html')).read_bytes()==content, f'prior edition changed by TOC labels: {slug}'
    section_body=linked_body+'\n## [Следующий `раздел`](https://example.com/section)\n\n### Четвёртая тема\n\nМатериал.\n'
    source.write_text(header+'navigation: top\ntoc: plain\n'+section_body)
    build(checkout)
    prior_article=output.read_text().split('<article class="prose">',1)[1].split('</article>',1)[0]
    source.write_text(header+'navigation: top\ntoc: sections\n'+section_body)
    build(checkout)
    rendered=output.read_text()
    reader=ReaderOrder(rendered)
    assert reader.order==['aside','article'], 'section navigation must retain the requested reading order'
    assert reader.links==['section-1','section-4'], 'section navigation must link only to H2 headings, preserving their anchors'
    assert reader.toc_labels==['Первая тема','Следующий раздел'], 'section navigation must show plain section labels'
    assert reader.headings==['section-1','section-2','section-3','section-4','section-5'], 'section navigation must retain every article heading'
    assert rendered.split('<article class="prose">',1)[1].split('</article>',1)[0]==prior_article, 'section navigation must not change article content or source links'
    for slug,content in prior.items():
        assert (checkout/'_site'/(slug+'.html')).read_bytes()==content, f'prior edition changed by section navigation: {slug}'
    story_urls=[f'https://example.com/navigation-fixture/story-{n}' for n in range(50)]
    practice_urls=[f'https://example.com/navigation-fixture/practice-{n}' for n in range(3)]
    archive_body='---\n# Проверка навигации\n\n## Главное\n\n'
    archive_body+='\n'.join(f'### [Сюжет {n}]({url})\n\nОпыт компании.\n' for n,url in enumerate(story_urls[:-1]))
    archive_body+='\n## Что из этого применить в платформе\n\n'
    archive_body+='\n'.join(f'### Практическая группа {n}\n\n**Предложение.** [Опора]({url})\n' for n,url in enumerate(practice_urls))
    archive_body+='\n## Коротко\n\n### Последний сюжет\n\n[Источник]('+story_urls[-1]+')\n'
    for toc_mode,expected_urls in [('plain',story_urls[:-1]+practice_urls+story_urls[-1:]),('sections',story_urls)]:
        source.write_text(header+'navigation: top\ntoc: '+toc_mode+'\n'+archive_body)
        build(checkout)
        urls=ArchiveFindings((checkout/'_site'/'findings.html').read_text()).urls
        fixture_urls=[url for url in urls if url.startswith('https://example.com/navigation-fixture/')]
        assert fixture_urls==expected_urls, f'{toc_mode}: archive must retain all 50 story H3, but exclude practice groups only with section navigation'
    for slug,content in prior.items():
        assert (checkout/'_site'/(slug+'.html')).read_bytes()==content, f'prior edition changed by practice groups: {slug}'
    source.write_text(header+'toc: typo\n'+body)
    rejected=subprocess.run([sys.executable,'build.py'],cwd=checkout,capture_output=True,text=True)
    assert rejected.returncode!=0 and 'invalid toc' in rejected.stderr, 'unsupported TOC mode accepted'
    source.write_text(header+'navigation: typo\n'+body)
    rejected=subprocess.run([sys.executable,'build.py'],cwd=checkout,capture_output=True,text=True)
    assert rejected.returncode!=0 and 'invalid navigation' in rejected.stderr, 'unsupported navigation accepted'
print('PASS: opt-in navigation reading order, H2-only sections, preserved article, 50 stories without practice groups, legacy archive, prior editions and metadata validation')
