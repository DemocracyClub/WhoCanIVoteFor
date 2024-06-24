from django import forms
from hustings.models import Husting


class CurrentElectionsChoiceField(forms.ModelChoiceField):
    def __init__(self, queryset, *args, **kwargs):
        queryset = queryset.filter(election__current=True)
        super().__init__(queryset, *args, **kwargs)


class AddHustingForm(forms.ModelForm):
    class Meta:
        model = Husting
        fields = ("post_election", "title", "starts", "url", "location")
        widgets = {
            "starts": forms.SplitDateTimeWidget(
                attrs={"type": "datetime-local"}
            ),
            "post_election": forms.HiddenInput,
        }

    # post_election = forms.CharField(widget=forms.HiddenInput)

    starts = forms.SplitDateTimeField(
        widget=forms.SplitDateTimeWidget(
            date_attrs={"type": "date"},
            time_attrs={"type": "time"},
        ),
        help_text="The date and time the event starts",
    )
    url = forms.URLField(
        required=True,
        label="URL",
        help_text="A webpage where people can find more information and/or sign up to attend",
    )
