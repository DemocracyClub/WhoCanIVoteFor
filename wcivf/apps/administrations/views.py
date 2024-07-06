# Create your views here.

from administrations.forms import YourAreaPostcodeForm
from administrations.helpers import AdministrationsHelper
from core.helpers import clean_postcode
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import TemplateView


class YourArea(TemplateView):
    template_name = "elections/your_area.html"
    form_class = YourAreaPostcodeForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["your_area_postcode_form"] = context.get(
            "form", self.form_class()
        )
        self.postcode = self.kwargs.get("postcode")
        if self.postcode:
            self.postcode = clean_postcode(self.postcode)
        else:
            return context

        self.uprn = self.kwargs.get("uprn")

        try:
            administrations = AdministrationsHelper(
                self.postcode, uprn=self.uprn
            )
            context["administrations"] = administrations
            if administrations.address_picker:
                context["address_picker"] = True
                context["addresses"] = administrations.addresses
        except Exception as e:
            print(str(e))
            # Just catch any error at the moment, as we don't want this to break anything
            pass
        return context

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        return HttpResponseRedirect(
            reverse(
                "your_area_view",
                kwargs={"postcode": form.cleaned_data["postcode"]},
            )
        )
