from urllib.parse import unquote_plus

from core.helpers import clean_postcode
from django.conf import settings

from .forms import PostcodeLookupForm


def use_compress_css(request):
    return {
        "USE_COMPRESSED_CSS": getattr(settings, "USE_COMPRESSED_CSS", False)
    }


def use_i18n(request):
    return {"USE_I18N": getattr(settings, "USE_I18N", False)}


def postcode_form(request):
    return {"postcode_form": PostcodeLookupForm()}


def referer_postcode(request):
    referer_parts = request.META.get("HTTP_REFERER", "")
    referer_parts = referer_parts.strip("/").split("/")
    if len(referer_parts) >= 2 and referer_parts[-2] == "elections":
        postcode_url_part = referer_parts[-1]
        possible_postcode = unquote_plus(postcode_url_part)
        cleaned_postcode = clean_postcode(possible_postcode)
        if len(cleaned_postcode) <= 8:
            return {"referer_postcode": cleaned_postcode}
    return {}
