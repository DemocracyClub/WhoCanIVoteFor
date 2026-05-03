# Create your views here.
from administrations.forms import YourAreaPostcodeForm
from administrations.helpers import AdministrationsHelper
from core.helpers import clean_postcode
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import TemplateView


class YourArea(TemplateView):
    template_name = "elections/your_area.html"
    form_class = YourAreaPostcodeForm

    def dispatch(self, request, *args, **kwargs):
        if not settings.ENABLE_LAYERS_OF_STATE_FEATURE:
            redirect_kwargs = {}
            view_name = "home_view"
            if postcode:= kwargs.get("postcode"):
                view_name = "postcode_view"
                redirect_kwargs["postcode"] = postcode
            if uprn := self.kwargs.get("uprn"):
                view_name = "uprn_view"
                redirect_kwargs["uprn"] = uprn
            return HttpResponseRedirect(reverse(view_name, kwargs=redirect_kwargs))
        return super().dispatch(request, *args, **kwargs)

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

        administrations = AdministrationsHelper(self.postcode, uprn=self.uprn)
        context["administrations"] = administrations
        if administrations.address_picker:
            context["address_picker"] = True
            context["addresses"] = administrations.addresses
            print(administrations.addresses)
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
