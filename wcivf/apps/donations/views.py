from django.views.generic import TemplateView


class DonateFormView(TemplateView):
    template_name = "donations/donate.html"


class DonateThanksView(TemplateView):
    template_name = "donate_thanks.html"
