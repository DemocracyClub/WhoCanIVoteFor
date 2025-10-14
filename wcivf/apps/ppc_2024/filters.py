import django_filters
from dc_utils.filter_widgets import DSLinkWidget
from ppc_2024.models import PPCPerson


class PPCFilter(django_filters.FilterSet):
    region = django_filters.AllValuesFilter(
        widget=DSLinkWidget,
        field_name="region_name",
        lookup_expr="contains",
        label="Region",
    )
    party_name = django_filters.AllValuesFilter(
        widget=DSLinkWidget,
        field_name="party__party_name",
        lookup_expr="exact",
        label="Party Name",
    )

    class Meta:
        model = PPCPerson
        fields = ["region"]
