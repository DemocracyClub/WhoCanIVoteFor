from django.conf import settings


def show_hustings_cta(request):
    return {"SHOW_HUSTINGS_CTA": getattr(settings, "SHOW_HUSTINGS_CTA", False)}
