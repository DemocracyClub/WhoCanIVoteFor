from django.conf.urls import url

from .views import DonateFormView, DonateThanksView

urlpatterns = [
    url(r"thanks", DonateThanksView.as_view(), name="donate_thanks"),
    url(r"", DonateFormView.as_view(), name="donate"),
]
