from pathlib import Path

from core.templatetags.markdown_filter import markdown_it_filter
from django.test import TestCase

allowed_markdown_input = """\
Bla bla bla

- unordered
- bullet
- list

**bold** _italic_

1. ordered
2. bullet
3. list
"""

allowed_markdown_expected = """\
<p>Bla bla bla</p>
<ul>
<li>unordered</li>
<li>bullet</li>
<li>list</li>
</ul>
<p><strong>bold</strong> <em>italic</em></p>
<ol>
<li>ordered</li>
<li>bullet</li>
<li>list</li>
</ol>
"""


class TestMarkdownFilters(TestCase):
    def test_xss(self):
        self.assertHTMLEqual(
            markdown_it_filter('<script>alert("xss")</script>'),
            "<p>&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;</p>\n",
        )

    def test_allowed_markdown(self):
        """
        Assert that the markdown styles we do want to support i.e:
        - lists
        - bold, italic
        - blockquote
        render as HTML
        """
        self.assertHTMLEqual(
            markdown_it_filter(allowed_markdown_input),
            allowed_markdown_expected,
        )

    def test_forbidden_markdown(self):
        """
        Assert that the markdown styles we don't want to support
        i.e: most of the markdown spec
        does not get rendered to HTML
        """
        test_cases = [
            "blockquote",
            "code",
            "headings",
            "horizontal_rules",
            "html",
            "images",
            "links",
            "strikethrough",
            "tables",
        ]
        for test_case in test_cases:
            with self.subTest(test_case=test_case):
                input_ = Path(
                    f"wcivf/apps/core/tests/forbidden_markdown/input/{test_case}.txt"
                ).read_text()
                expected = Path(
                    f"wcivf/apps/core/tests/forbidden_markdown/expected/{test_case}.txt"
                ).read_text()
                self.assertHTMLEqual(markdown_it_filter(input_), expected)
