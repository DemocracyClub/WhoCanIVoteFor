from django.conf import settings

from .forms import PostcodeLookupForm

# Remove this once we add all_settings to settings.CONTEXT_PROCESSORS
def canonical_url(request):
    return {'CANONICAL_URL': settings.CANONICAL_URL}


def all_settings(request):
    return {x: getattr(s, x) for x in dir(s)}


def use_compress_css(request):
    return {
        'USE_COMPRESSED_CSS': getattr(settings, 'USE_COMPRESSED_CSS', False)
    }

def postcode_form(request):
    return {
        'postcode_form': PostcodeLookupForm()
    }

