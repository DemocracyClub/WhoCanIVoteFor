from django import forms

from .models import (
    Feedback,
    FOUND_USEFUL_CHOICES,
    VOTE_CHOICES,
    generate_feedback_token,
)


class FeedbackForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FeedbackForm, self).__init__(*args, **kwargs)
        self.fields["token"].initial = generate_feedback_token()

    class Meta:
        model = Feedback
        fields = ["found_useful", "sources", "vote", "comments", "source_url"]

    found_useful = forms.ChoiceField(
        choices=FOUND_USEFUL_CHOICES,
        widget=forms.RadioSelect(attrs={"data-toggle": "button"}),
    )
    vote = forms.ChoiceField(
        choices=VOTE_CHOICES,
        widget=forms.RadioSelect(attrs={"data-toggle": "button"}),
    )
    source_url = forms.CharField(widget=forms.HiddenInput())
    token = forms.CharField(widget=forms.HiddenInput())
