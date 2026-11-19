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
    resolved_referer = _resolve_referer(request)

    if resolved_referer is None or "postcode" not in resolved_referer.kwargs:
        return {}

    postcode_kwarg = resolved_referer.kwargs["postcode"]
    referer_postcode = unquote_plus(postcode_kwarg)
    try:
        referer_postcode = validate_postcode(referer_postcode)
    except ValidationError:
        return {}
    return {"referer_postcode": referer_postcode}


def referer_uprn(request):
    resolved_referer = _resolve_referer(request)

    if resolved_referer is None or "uprn" not in resolved_referer.kwargs:
        return {}

    uprn_kwarg = resolved_referer.kwargs["uprn"]
    referer_uprn = uprn_kwarg

    if not referer_uprn.isdigit():
        return {}

    return {"referer_uprn": referer_uprn}


def _resolve_referer(request):
    referer = request.META.get("HTTP_REFERER", "")
    if not referer:
        return None

    referer = urlparse(referer)
    if referer.hostname not in settings.ALLOWED_HOSTS:
        return None

    referer_path = referer.path
    if referer_path.startswith("/elections/"):
        try:
            return resolve(referer_path)
        except Resolver404:
            return None
    return None
