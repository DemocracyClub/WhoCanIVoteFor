import markdown
import nh3
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="markdown")
def markdown_filter(text):
    clean_text = nh3.clean(text)
    return mark_safe(markdown.markdown(clean_text, extensions=["nl2br"]))


markdown_filter.is_safe = True
