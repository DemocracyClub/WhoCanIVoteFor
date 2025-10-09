import markdown
import nh3
from django import template
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

register = template.Library()


@register.filter(name="markdown")
def markdown_filter(text):
    clean_text = nh3.clean(text)
    return mark_safe(markdown.markdown(clean_text, extensions=["nl2br"]))


markdown_filter.is_safe = True


@register.filter(name="markdown_subset")
def markdown_it_filter(text):
    """
    note using js-default preset here gives us XSS protection
    https://markdown-it-py.readthedocs.io/en/latest/security.html
    so we don't need to run the text through nh3
    """
    options = {
        "breaks": True  # nl2br
    }
    renderer = MarkdownIt("js-default", options).disable(
        [
            "table",
            "code",
            "fence",
            "blockquote",
            "backticks",
            "hr",
            "reference",
            "html_block",
            "heading",
            "lheading",
            "linkify",
            "strikethrough",
            "link",
            "image",
            "autolink",
            "html_inline",
        ]
    )
    html = renderer.render(text)
    return mark_safe(html)


markdown_it_filter.is_safe = True
