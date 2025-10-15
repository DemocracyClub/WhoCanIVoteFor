import django_filters
from dc_utils.filter_widgets import DSLinkWidget
from elections.models import Election


def election_types_choices():
    return [
        ("europarl", "European Parliament"),
        ("gla", "London Assembly"),
        ("local", "Local"),
        ("mayor", "Mayoral"),
        ("pcc", "Police and Crime Commissioner"),
        ("nia", "Northern Ireland Assembly"),
        ("ref", "Referendum"),
        ("sp", "Scottish Parliament"),
        ("senedd", "Senedd Cymru"),
        ("parl", "UK Parliament"),
    ]


class ElectionTypeFilter(django_filters.FilterSet):
    def election_type_filter(self, queryset, name, value):
        if value == "senedd":
            return queryset.filter(election_type__in=["senedd", "naw"])
        return queryset.filter(election_type=value)

    election_type = django_filters.ChoiceFilter(
        widget=DSLinkWidget,
        method="election_type_filter",
        choices=election_types_choices,
        label="Election Type",
        help_text="A valid [election type](https://elections.democracyclub.org.uk/election_types/)",
    )

    class Meta:
        model = Election
        fields = ["election_type"]
