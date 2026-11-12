"""Old heading links land at their topic after a compact-reader reorder."""
from pathlib import Path
from html.parser import HTMLParser
import shutil
import subprocess
import sys
import tempfile
import unittest
import build


class IDs(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.ids.extend(value for name, value in attrs if name == 'id')


class LegacyAnchors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.checkout = Path(cls.temp.name) / 'site'
        shutil.copytree(build.ROOT, cls.checkout,
                        ignore=shutil.ignore_patterns('.git', '_site', '__pycache__'))
        cls.source = cls.checkout / 'content' / '2026-11-12-legacy-test.md'

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def render(self, mapping=None, *, compact=True, reserved=False, body=None):
        metadata = 'date: 2026-11-12\ntype: daily\ntitle: Test\n'
        if compact:
            metadata += 'format: compact\n'
        if mapping is not None:
            metadata += 'legacy_heading_map: ' + mapping + '\n'
        if reserved:
            metadata += 'reserved_heading_ids: 1,5\n'
        body = body or ('# Test\n\n## Intro\n\nIntroduction.\n\n➡️ **Новости**\n\n'
                '🔹 First topic. [Source](https://example.com/first)\n\n'
                '🔥 **Hot**\n\n🔹 Second topic. [Source](https://example.com/second)\n')
        self.source.write_text('---\n' + metadata + '---\n' + body)
        result = subprocess.run([sys.executable, 'build.py'], cwd=self.checkout,
                                capture_output=True, text=True)
        return result

    def test_old_links_land_at_reordered_topics_sections_and_top_without_duplicates(self):
        result = self.render('section-1=finding-2,section-2=compact-section-1,'
                             'section-3=main,section-4=finding-2', reserved=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (self.checkout / '_site' / '2026-11-12-legacy-test.html').read_text()
        self.assertIn('<span id="section-1"></span>\n<span id="section-4"></span>\n<p id="finding-2">', page)
        self.assertIn('<span id="section-2"></span>\n<p id="compact-section-1">', page)
        self.assertLess(page.index('id="section-3"'), page.index('Introduction.'))
        self.assertIn('<h2 id="section-6">Intro</h2>', page)
        ids = IDs(page).ids
        self.assertEqual(len(ids), len(set(ids)), ids)
        for target in ('main', 'finding-1', 'finding-2', 'compact-section-1', 'compact-section-2'):
            self.assertIn(target, ids)

    def test_mapping_rejects_missing_or_unsafe_targets_and_duplicate_keys(self):
        for mapping in ('section-1=finding-3', 'section-1=compact-section-3',
                        'section-1=section-2', 'section-0=main',
                        'section-1=finding-0', 'section-01=main',
                        'section-1=main,section-1=finding-1',
                        'section-1=main,', 'section-1=main onclick=x',
                        'section-1=main, section-2=main'):
            with self.subTest(mapping=mapping):
                result = self.render(mapping)
                self.assertNotEqual(result.returncode, 0, mapping)
                self.assertIn('legacy', result.stderr.lower())

    def test_target_must_be_emitted_in_html_not_only_recognized_in_outline(self):
        result = self.render('section-1=finding-1', body=(
            '# Test\n\n➡️ **Новости**\n'
            '🔹 Topic without a paragraph boundary. [Source](https://example.com/topic)\n'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('legacy', result.stderr.lower())

    def test_mapping_requires_compact_format(self):
        result = self.render('section-1=main', compact=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('legacy', result.stderr.lower())

    def test_unmapped_ordinary_page_keeps_heading_ids(self):
        result = self.render(compact=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (self.checkout / '_site' / '2026-11-12-legacy-test.html').read_text()
        self.assertIn('<h2 id="section-1">Intro</h2>', page)
        self.assertNotIn('id="finding-', page)


if __name__ == '__main__':
    unittest.main()
