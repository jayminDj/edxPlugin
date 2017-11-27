"""
View for Courseware Index list
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
@api {get} /api-pural/courses/:courseId/chapters Provides list of chapters with its associate section
@apiGroup ChapterContext
@apiName getChapterContext
@apiSampleRequest http://localhost:8000/api-pural/courses/course-v1:PROMACT+DP1+2017_T1/chapters
@apiHeader {String} Authorization User's Outh-token

@apiParam {string} courseId course unique Id

@apiSuccess {Objects[]} chapters list of chapters with sections

@apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
        "next_of_active_section": null,
        "previous_of_active_section": null,
        "chapters": [
                {
                    "display_id": "module-1",
                    "sections": [
                        {
                            "url_name": "7a33b05099004bccbf5ea334489c40b0",
                            "display_name": "HTML Module",
                            "graded": false,
                            "format": "",
                            "due": null,
                            "active": false
                        }
                    ],
                    "url_name": "95d83a1f57af46d9b25a9c7415d8f565",
                    "display_name": "Module 1",
                    "active": false
                }
            ]
        }

@apiUse MyError

"""
@can_disable_rate_limit
class CoursewareIndexList(APIView,ApiKeyPermissionMixIn,courseaccess):


    authentication_classes = OAuth2AuthenticationAllowInactiveUser, SessionAuthenticationAllowInactiveUser
    permission_classes = ApiKeyHeaderPermissionIsAuthenticated,
    throttle_classes = EnrollmentUserThrottle,

    @method_decorator(ensure_csrf_cookie_cross_domain)
    @method_decorator(ensure_valid_course_key)
    def get(self, request, course_id,chapter=None, section=None, position=None):

        """
                Displays courseware chapters list  for enrolled caourses.
                Arguments:
                    request: HTTP request
                    course_id (unicode): course id
                    chapter (unicode): chapter url_name
                    section (unicode): section url_name
                    position (unicode): position in module, eg of <sequential> module
        """

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
            table_of_contents = self._get()
            return Response(
                status=status.HTTP_200_OK,
                data=table_of_contents
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
        find all course content's class objects and find uses 
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
        returns the chapter list base on course
        """
        table_of_contents = toc_for_course(
            self.effective_user,
            self.request,
            self.course,
            self.chapter_url_name,
            self.section_url_name,
            self.field_data_cache,
        )

        return table_of_contents


