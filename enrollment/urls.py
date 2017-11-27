
from django.conf import settings
from django.conf.urls import patterns, url, include

from .views import (
    EnrollmentView,
    EnrollmentListView,
    EnrollmentCourseDetailView
)

"""
urlpatterns = patterns(
    '',
    url(r'^enrollment$', EnrollmentListView.as_view(), name='courseenrollments')
)
"""

urlpatterns = patterns(
    'enrollment.views',
    url(
        r'^enrollment/{username},{course_key}$'.format(
            username=settings.USERNAME_PATTERN, course_key=settings.COURSE_ID_PATTERN
        ),
        EnrollmentView.as_view(),
        name='api_courseenrollment'
    ),
    url(
        r'^enrollment/{course_key}$'.format(course_key=settings.COURSE_ID_PATTERN),
        EnrollmentView.as_view(),
        name='api_courseenrollment'
    ),
    url(r'^enrollment$', EnrollmentListView.as_view(), name='courseenrollments'),
    url(
        r'^course/{course_key}$'.format(course_key=settings.COURSE_ID_PATTERN),
        EnrollmentCourseDetailView.as_view(),
        name='api_courseenrollmentdetails'
    ),
)