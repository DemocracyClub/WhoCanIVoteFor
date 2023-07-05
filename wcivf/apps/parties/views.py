from django.views.generic import ListView, DetailView

from .models import Party


class PartiesView(ListView):
    queryset = Party.objects.exclude(personpost=None)


class PartyView(DetailView):
    def get_template_names(self):
        party_id = self.object.party_id

        if party_id == "ynmp-party:2":
            return ["parties/independent_candidate.html"]

        if party_id == "ynmp-party:12522":
            return ["parties/speaker_seeking_reelection.html"]

        return ["parties/party_detail.html"]

    queryset = Party.objects.all()
