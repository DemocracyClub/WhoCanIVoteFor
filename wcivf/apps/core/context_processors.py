from urllib.parse import unquote_plus, urlparse

from core.helpers import validate_postcode
from django.conf import settings
from django.forms import ValidationError
from django.urls import Resolver404, resolve

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
    referer = request.META.get("HTTP_REFERER", "")

    if not referer:
        return {}

    referer_path = urlparse(referer).path
    if not referer_path.startswith("/elections"):
        return {}

    try:
        match = resolve(referer_path)
    except Resolver404:
        return {}

    if "postcode" not in match.kwargs:
        return {}

    postcode_kwarg = match.kwargs["postcode"]
    referer_postcode = unquote_plus(postcode_kwarg)
    try:
        referer_postcode = validate_postcode(referer_postcode)
    except ValidationError:
        return {}
    return {"referer_postcode": referer_postcode}
