

from django.conf import settings
from django.conf.urls import patterns, url
from .views import courseDiscovery

urlpatterns = patterns(
    '',
    url(r'^course_discovery/?$', courseDiscovery.as_view()),
)