import itertools
from datetime import datetime, timedelta

from django.views.generic import TemplateView

from elections.models import Election
from results.models import ResultEvent


class ResultsListView(TemplateView):
    template_name = "results/results_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['elections'] = []
        election_qs = Election.objects.filter(
            current=True).order_by('-election_weight')
        for election in election_qs:

            results1 = ResultEvent.objects.filter(
                post_election__election=election,
                declaration_time__isnull=False
            ).order_by('-declaration_time').select_related(
                'post_election',
                'post_election__election',
                'post_election__post',
            ).prefetch_related(
                'person_posts',
                'person_posts__post',
                'person_posts__person',
                'person_posts__party',
            )

            results2 = ResultEvent.objects.filter(
                post_election__election=election,
                declaration_time__isnull=True
            ).order_by('-expected_declaration_time').select_related(
                'post_election',
                'post_election__election',
                'post_election__post',
            ).prefetch_related(
                'person_posts__post__area_name',
                'person_posts__person',
                'person_posts__party',
            )
            results = []

            for r in results1:
                r.declaration_time = \
                    r.declaration_time + timedelta(hours=1)
                results.append(r)
            for r in results2:
                results.append(r)
            for i, r in enumerate(results):
                r.rank_order = i
                # Hack to deal with these dates being stored wrongly!
                # Fix after election night.
                if r.expected_declaration_time:
                    r.expected_declaration_time = \
                        r.expected_declaration_time + timedelta(hours=1)
            election_dict = {
                'election': election,
                'results': results
            }
            context['elections'].append(election_dict)
        return context
