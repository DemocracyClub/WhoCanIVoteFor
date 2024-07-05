# Create your views here.
from administrations.helpers import AdministrationsHelper
from core.helpers import clean_postcode
from django.views.generic import TemplateView


class YourArea(TemplateView):
    template_name = "elections/your_area.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        self.postcode = clean_postcode(kwargs["postcode"])
        self.uprn = self.kwargs.get("uprn")

        try:
            administrations = AdministrationsHelper(
                self.postcode, uprn=self.uprn
            )
            context["administrations"] = administrations
            if administrations.address_picker:
                context["address_picker"] = True
                context["addresses"] = administrations.addresses
        except Exception:
            # Just catch any error at the moment, as we don't want this to break anything
            pass

        return context
