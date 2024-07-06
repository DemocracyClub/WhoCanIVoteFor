from django.urls import re_path

from .views import YourArea

urlpatterns = [
    re_path(
        r"^(?P<postcode>[^/]+)/(?P<uprn>[^/]+)/$",
        YourArea.as_view(),
        name="your_area_view",
    ),
    re_path(
        r"^(?P<postcode>[^/]+)/$",
        YourArea.as_view(),
        name="your_area_view",
    ),
    re_path(
        r"^$",
        YourArea.as_view(),
        name="your_area_view",
    ),
]
