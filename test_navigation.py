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
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attributes=dict(attributes)
        if tag in ('article','aside'):
            self.order.append(tag)
        if tag=='a' and attributes.get('href','').startswith('#section-'):
            self.links.append(attributes['href'][1:])
        if tag in ('h2','h3'):
            self.headings.append(attributes.get('id'))


def build(checkout):
    subprocess.run([sys.executable,'build.py'],cwd=checkout,check=True,capture_output=True,text=True)


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
    source.write_text(header+'navigation: typo\n'+body)
    rejected=subprocess.run([sys.executable,'build.py'],cwd=checkout,capture_output=True,text=True)
    assert rejected.returncode!=0 and 'invalid navigation' in rejected.stderr, 'unsupported navigation accepted'
print('PASS: opt-in navigation reading order, section targets, prior editions and metadata validation')
