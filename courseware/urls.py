
from django.conf import settings
from django.conf.urls import patterns, url, include
from views.index import CoursewareIndex
from views.index_list import CoursewareIndexList
from views.context_list import CoursewareContextList

urlpatterns = patterns(
    '',
    url(
        r'^{}/courseware/(?P<chapter>[^/]*)/(?P<section>[^/]*)/(?P<position>[^/]*)/(?P<component>[^/]*)/?$'.format(
            settings.COURSE_ID_PATTERN,
        ),
        CoursewareIndex.as_view(),
        name='plug_api_courseware_position_content',
    ),
    url(
        r'^{}/chapters/?$'.format(
            settings.COURSE_ID_PATTERN,
        ),
        CoursewareIndexList.as_view(),
        name='plug_api_courseware_chapters_list',
    ),
    url(
        r'^{}/context/(?P<chapter>[^/]*)/(?P<section>[^/]*)/(?P<position>[^/]*)/?$'.format(
            settings.COURSE_ID_PATTERN,
        ),
        CoursewareContextList.as_view(),
        name='plug_api_courseware_chapters_context_list',
    ),
)