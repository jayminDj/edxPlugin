"""
URLs for pural-pugin
"""

from django.conf import settings
from django.conf.urls import patterns, url, include



urlpatterns = patterns(
    '',
     url(r'^enrollment/v1/', include('puralPlugin.enrollment.urls')),
     url(r'^courses/', include('puralPlugin.courseware.urls')),
     url(r'^search/', include('puralPlugin.search.urls'))
)
