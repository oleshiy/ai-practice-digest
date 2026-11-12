"""Renamed releases remain one edition and keep old deep links working."""
from pathlib import Path
import re, shutil, subprocess, sys, tempfile
import build

with tempfile.TemporaryDirectory() as temp:
    checkout=Path(temp)/'site'
    shutil.copytree(build.ROOT,checkout,ignore=shutil.ignore_patterns('.git','_site','__pycache__'))
    content=checkout/'content'
    old=content/'2026-11-09-daily.md'
    if not old.exists():
        old=content/'astra-2026-11-09-daily.md'
    original=re.sub(r'^redirect_from: .*\n','',old.read_text(),flags=re.MULTILINE)
    old.unlink()
    renamed=content/'astra-2026-11-09-daily.md'
    renamed.write_text(original.replace('---\n','---\nredirect_from: 2026-11-09-daily\n',1))
    def run():
        return subprocess.run([sys.executable,'build.py'],cwd=checkout,capture_output=True,text=True)
    result=run()
    assert result.returncode==0,result.stderr
    subprocess.run([sys.executable,'check.py'],cwd=checkout,check=True)
    site=checkout/'_site'
    new=(site/'astra-2026-11-09-daily.html').read_text()
    alias=(site/'2026-11-09-daily.html').read_text()
    assert '<article class="prose">' in new and '<article class="prose">' not in alias
    assert 'http-equiv="refresh" content="0;url=astra-2026-11-09-daily.html"' in alias
    assert 'location.hash' in alias and 'location.replace' in alias
    assert '<link rel="canonical" href="'+build.BASE+'astra-2026-11-09-daily.html"' in alias
    for name in ('index.html','archive.html'):
        text=(site/name).read_text()
        assert 'href="astra-2026-11-09-daily.html"' in text
        assert 'href="2026-11-09-daily.html"' not in text
    for invalid in ('../escape','https://example.com/redirect','astra-2026-11-09-daily','2026-11-01-weekly','comparison-2026-09-28-blind-b'):
        renamed.write_text(original.replace('---\n','---\nredirect_from: '+invalid+'\n',1))
        rejected=run()
        assert rejected.returncode!=0,invalid
    renamed.write_text(original)
    collision=content/'comparison-2026-09-28-blind-b.md'
    renamed.rename(collision)
    assert run().returncode!=0, 'edition collides with comparison'
    collision.rename(renamed)
    renamed.rename(content/'invalid-prefix!.md')
    assert run().returncode!=0
rendered,_=build.markdown('# Выпуск\n\n## Практика\n\n### Первая\n\n### Вторая\n\n## Безопасность\n\n### Тема\n',reserved_heading_ids=(4,5))
assert '<h2 id="section-6">Безопасность</h2>' in rendered
assert '<h3 id="section-7">Тема</h3>' in rendered
assert 'id="section-4"' in rendered and 'id="section-5"' in rendered
print('PASS: prefixed release, single indexed edition, canonical alias, deep links and invalid/colliding aliases')
