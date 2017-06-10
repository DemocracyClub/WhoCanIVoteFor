from django.conf.urls import include, url
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.sitemaps.views import sitemap
from django.views.decorators.cache import cache_page

from elections.sitemaps import ElectionSitemap, PostElectionSitemap
from people.sitemaps import PersonSitemap
from parties.sitemaps import PartySitemap

sitemaps = {
    'elections': ElectionSitemap,
    'postelections': PostElectionSitemap,
    'people': PersonSitemap,
    'parties': PartySitemap,
}

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('core.urls')),
    url(r'^elections/', include('elections.urls')),
    url(r'^results/', include('results.urls')),
    url(r'^parties/', include('parties.urls')),
    url(r'^person/', include('people.urls')),
    url(r'^feedback/', include('feedback.urls')),
    url(r'^api/', include('api.urls', namespace="api")),
    url(r'^sitemap\.xml$', cache_page(86400)(sitemap), {'sitemaps': sitemaps},
        name='django.contrib.sitemaps.views.sitemap'),
    url(r'^robots\.txt', include('robots.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
