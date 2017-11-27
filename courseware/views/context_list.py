"""
View for Courseware context list
"""
# pylint: disable=attribute-defined-outside-init

from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import View
import logging
import newrelic.agent
import urllib
from util.views import ensure_valid_course_key
from xmodule.x_module import STUDENT_VIEW

from courseware.module_render import toc_for_course, get_module_for_descriptor
from ..courseaccess import courseaccess
from openedx.core.lib.api.authentication import (
    SessionAuthenticationAllowInactiveUser,
    OAuth2AuthenticationAllowInactiveUser,
)
from openedx.core.lib.api.permissions import ApiKeyHeaderPermission, ApiKeyHeaderPermissionIsAuthenticated
from openedx.core.djangoapps.cors_csrf.authentication import SessionAuthenticationCrossDomainCsrf
from rest_framework.throttling import UserRateThrottle
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.cors_csrf.decorators import ensure_csrf_cookie_cross_domain
from util.disable_rate_limit import can_disable_rate_limit
from ...exceptions import Http401



log = logging.getLogger("edx.courseware.views.index")
TEMPLATE_IMPORTS = {'urllib': urllib}
CONTENT_DEPTH = 2


class EnrollmentCrossDomainSessionAuth(SessionAuthenticationAllowInactiveUser, SessionAuthenticationCrossDomainCsrf):
    """Session authentication that allows inactive users and cross-domain requests. """
    pass


class ApiKeyPermissionMixIn(object):
    """
    This mixin is used to provide a convenience function for doing individual permission checks
    for the presence of API keys.
    """
    def has_api_key_permissions(self, request):
        """
        Checks to see if the request was made by a server with an API key.

        Args:
            request (Request): the request being made into the view

        Return:
            True if the request has been made with a valid API key
            False otherwise
        """
        return ApiKeyHeaderPermission().has_permission(request, self)


class EnrollmentUserThrottle(UserRateThrottle, ApiKeyPermissionMixIn):
    """Limit the number of requests users can make to the enrollment API."""
    rate = '40/minute'

    def allow_request(self, request, view):
        return self.has_api_key_permissions(request) or super(EnrollmentUserThrottle, self).allow_request(request, view)


"""
@api {get} /api-pural/courses/:courseId/context/:chapterId/:sectionId/ Provides list of sequences in section
@apiGroup SectionContext
@apiName getSectionContext
@apiSampleRequest http://localhost:8000/api-pural/courses/course-v1:PROMACT+DP1+2017_T1/context/95d83a1f57af46d9b25a9c7415d8f565/7a33b05099004bccbf5ea334489c40b0/
@apiHeader {String} Authorization User's Outh-token

@apiParam {string} courseId course unique Id
@apiParam {string} chapterId chapter unique Id of course
@apiParam {string} sectionId section unique Id of chapter


@apiSuccess {String}   section section name of chapter
@apiSuccess {String}   url_name unique id of section
@apiSuccess {Objects[]} sequences list of position in sequences

@apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
        "section": "HTML Module",
        "url_name": "7a33b05099004bccbf5ea334489c40b0",
            "sequences": [
                {
                    "graded": false,
                    "has_children": true,
                    "is_entrance_exam": false,
                    "showanswer": "finished",
                    "childrens": [
                        {
                            "category": "video",
                            "url_name": "81fc303511e04c07b860c7b9c10b7f9d",
                            "display_name": "Video",
                            "display_name_with_default_escaped": "Video"
                        },
                        {
                            "category": "video",
                            "url_name": "09fc75999cb44df89acb735d6a44b1b2",
                            "display_name": "Video",
                            "display_name_with_default_escaped": "Video"
                        }
                    ],
                    "category": "vertical",
                    "url_name": "a235b099aca648acac6732bfbe61dc01",
                    "display_name": "Announcement content",
                    "has_score": false,
                    "start": "2017-05-10T07:00:00Z",
                    "display_name_with_default_escaped": "Announcement content"
                }
            ]
        }

@apiUse MyError

"""


@can_disable_rate_limit
class CoursewareContextList(APIView,ApiKeyPermissionMixIn,courseaccess):

    authentication_classes = OAuth2AuthenticationAllowInactiveUser, SessionAuthenticationAllowInactiveUser
    permission_classes = ApiKeyHeaderPermissionIsAuthenticated,
    throttle_classes = EnrollmentUserThrottle,

    @method_decorator(ensure_csrf_cookie_cross_domain)
    @method_decorator(ensure_valid_course_key)
    def get(self, request, course_id,chapter=None, section=None, position=None):

        self.course_key = CourseKey.from_string(course_id)
        self.request = request
        self.original_chapter_url_name = chapter
        self.original_section_url_name = section
        self.chapter_url_name = chapter
        self.section_url_name = section
        self.position = position
        self.chapter, self.section = None, None
        self.url = request.path

        try:
            self._init_new_relic()
            self._get_course_module()
            self.effective_user = self.request.user
            data = self._get()
            return Response(
                status=status.HTTP_200_OK,
                data=data
            )
        except UnicodeEncodeError:
            raise Http404("URL contains Unicode characters")
        except Http404:
            # let it propagate
            raise
        except Http401 as ex:
            return Response(
                status=status.HTTP_401_UNAUTHORIZED,
                data={
                    "message": (u"{message}").format(message=ex.args[0])
                }
            )
        except:# pylint: disable=broad-except
            return Response(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                data={
                    "message": (u"internal server error ")
                }
            )

    def _get(self):

        """
        find course's section , chapters content's class objects and find uses 
        enrollment to course 
        """
        self._redirect_if_needed_to_access_course()
        self._prefetch_and_bind_course()

        if self.course.has_children_at_depth(CONTENT_DEPTH):
            self.chapter = self._find_chapter()
            self.section = self._find_section()

            if self.chapter and self.section:
                self._prefetch_and_bind_section()

        return self._create_courseware_context()


    def _create_courseware_context(self):
        """
        returns section's sequnces with its child vertical module's context. 
        """

        courseware_context= {}
        section_context_data = {
            'section': None,
            'url_name': None,
            'sequences': []
        }

        table_of_contents = toc_for_course(
            self.effective_user,
            self.request,
            self.course,
            self.chapter_url_name,
            self.section_url_name,
            self.field_data_cache,
        )

        if self.section is not None:
            courseware_context['section_title'] = self.section.display_name_with_default_escaped
            section_context = self._create_section_context(
                table_of_contents['previous_of_active_section'],
                table_of_contents['next_of_active_section'],
            )

            """
            fetch section's context data
            """
            sequence_module = self._prefetch_sequence_context(self.section,STUDENT_VIEW, section_context)

            section_context_data = {
                'section':self.section.display_name,
                'url_name':self.section.url_name,
                'sequences':sequence_module
            }

        return section_context_data


    def _create_section_context(self, previous_of_active_section, next_of_active_section):
        """
        Returns and creates the rendering context for the section.
        """
        def _compute_section_url(section_info, requested_child):
            """
            Returns the section URL for the given section_info with the given child parameter.
            """
            return "{url}?child={requested_child}".format(
                url=reverse(
                    'courseware_section',
                    args=[unicode(self.course_key), section_info['chapter_url_name'], section_info['url_name']],
                ),
                requested_child=requested_child,
            )

        section_context = {
            'activate_block_id': self.request.GET.get('activate_block_id'),
            'requested_child': self.request.GET.get("child"),
            'progress_url': reverse('progress', kwargs={'course_id': unicode(self.course_key)}),
        }
        if previous_of_active_section:
            section_context['prev_url'] = _compute_section_url(previous_of_active_section, 'last')
        if next_of_active_section:
            section_context['next_url'] = _compute_section_url(next_of_active_section, 'first')

        return section_context