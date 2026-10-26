"""Figures retain attribution and cannot introduce active content or escape assets."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import build
from archive_page import findings

IMAGE='assets/memcurrent-architecture.png'
class Figures(unittest.TestCase):
    def test_figure_with_escaped_alt_and_caption(self):
        result,toc=build.markdown('![Слой "памяти" <script> &](%s)\nПодпись: <script>alert(1)</script> [Databricks](https://www.databricks.com/blog/memcurrent-designing-persistent-memory-production-agents)'%IMAGE)
        self.assertIn('<figure',result)
        self.assertIn('alt="Слой &quot;памяти&quot; &lt;script&gt; &amp;"',result)
        self.assertIn('<figcaption>',result)
        self.assertIn('Открыть в полном размере',result)
        self.assertNotIn('<script>',result)
        self.assertEqual(toc,[])
    def test_invalid_sources_and_caption_rejected(self):
        for source in ['javascript:alert(1)','data:image/svg+xml,x','https://example.com/x.png','//example.com/x.png','assets/../x.png','assets/x.svg','assets/missing.png','assets/x.png?foo=1']:
            with self.subTest(source=source),self.assertRaises(ValueError):build.markdown('![Фото](%s)\nПодпись: источник'%source)
        with self.assertRaises(ValueError):build.markdown('![Фото](%s)'%IMAGE)
        with self.assertRaises(ValueError):build.markdown('![Фото](%s)\nПодпись: [x](javascript:bad)'%IMAGE)
    def test_non_png_asset_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'assets').mkdir()
            (root/'assets'/'bad.png').write_text('<script>alert(1)</script>')
            with patch.object(build,'ROOT',root),self.assertRaises(ValueError):
                build.figure_asset('assets/bad.png')
    def test_archive_omits_figure_syntax(self):
        result=findings([{'date':'2026-10-25','slug':'test','title':'test','body':'### Title\n![Фото](%s)\nПодпись: [Image credit](https://wrong.example)\nText.\nИсточник: [Article](https://correct.example)'%IMAGE}])
        self.assertEqual(result[0]['url'],'https://correct.example')
        self.assertNotIn('![',result[0]['body'])
        self.assertNotIn('Подпись:',result[0]['body'])

if __name__=='__main__':unittest.main()
