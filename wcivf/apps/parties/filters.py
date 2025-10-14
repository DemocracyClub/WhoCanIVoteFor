from urllib.parse import urlencode

import django_filters
from dc_utils.filter_widgets import DSLinkWidget
from parties.models import Party


def party_register_choices():
    return [
        ("GB", "Great Britain"),
        ("NI", "Northern Ireland"),
    ]


def party_status_choices():
    return [("Registered", "Registered"), ("Deregistered", "Deregistered")]


class PartyRegisterFilter(django_filters.FilterSet):
    def party_register_filter(self, queryset, name, value):
        return queryset.filter(register=value)

    def party_status_filter(self, queryset, name, value):
        return queryset.filter(status=value)

    def party_nations_filter(self, queryset, name, value):
        return queryset.filter(nations__contains=[value])

    register = django_filters.ChoiceFilter(
        widget=DSLinkWidget,
        method="party_register_filter",
        choices=party_register_choices,
        label="Party Register",
    )

    status = django_filters.ChoiceFilter(
        widget=DSLinkWidget,
        method="party_status_filter",
        choices=party_status_choices,
        label="Party Status",
    )

    nations = django_filters.ChoiceFilter(
        widget=DSLinkWidget,
        method="party_nations_filter",
        choices=[("ENG", "England"), ("WAL", "Wales"), ("SCO", "Scotland")],
        label="Nation",
    )

    class Meta:
        model = Party
        fields = ["register", "status", "nations"]

    @property
    def shortcuts(self):
        """
        Returns filter shorcuts
        """
        shortcut_list = [
            {
                "name": "gb_parties",
                "label": "Registered in Great Britain",
                "query": {"register": ["GB"], "status": ["Registered"]},
            },
            {
                "name": "ni_parties",
                "label": "Registered in Northern Ireland",
                "query": {"register": ["NI"], "status": ["Registered"]},
            },
            {
                "name": "gb_dereg_parties",
                "label": "Deregistered in Great Britain",
                "query": {"register": ["GB"], "status": ["Deregistered"]},
            },
            {
                "name": "ni_dereg_parties",
                "label": "Deregistered in Northern Ireland",
                "query": {"register": ["NI"], "status": ["Deregistered"]},
            },
        ]

        query = dict(self.request.GET)
        shortcuts = {"list": shortcut_list}
        for shortcut in shortcuts["list"]:
            shortcut["querystring"] = urlencode(shortcut["query"], doseq=True)
            if shortcut["query"] == query:
                shortcut["active"] = True
                shortcuts["active"] = shortcut
        return shortcuts
