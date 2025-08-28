from django import forms

from .models import (
    FOUND_USEFUL_CHOICES,
    VOTE_CHOICES,
    Feedback,
    NoElectionFeedback,
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
        required=False,
    )
    email = forms.EmailField(required=False)
    source_url = forms.CharField(widget=forms.HiddenInput())
    token = forms.CharField(widget=forms.HiddenInput())


class NoElectionFeedbackForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(NoElectionFeedbackForm, self).__init__(*args, **kwargs)
        self.fields["token"].initial = generate_feedback_token()

    class Meta:
        model = NoElectionFeedback
        fields = ["no_election_feedback_text", "source_url"]

    no_election_feedback_text = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "cols": 40,
            }
        ),
        required=True,
    )
    source_url = forms.CharField(widget=forms.HiddenInput())
    token = forms.CharField(widget=forms.HiddenInput())
