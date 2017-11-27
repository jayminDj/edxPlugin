"""
View for Courseware content
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
@apiDefine MyError
@apiErrorExample {json} Error-Response:
      HTTP/1.1 401 UNAUTHORIZED
      {
        "detail": "Authentication credentials were not provided."
      }

@apiErrorExample {json} Error-Response:
      HTTP/1.1 404 NOT FOUND
      {
      "detail": "Not found."
      }
"""

"""
@api {get} /api-pural/courses/:courseId/courseware/:chapterId/:sectionId/:positionId/:componentId Provides component's content which part of Sequneces
@apiGroup ComponentContent
@apiName getComponentContent
@apiSampleRequest http://localhost:8000/api-pural/courses/course-v1:PROMACT+DP1+2017_T1/courseware/95d83a1f57af46d9b25a9c7415d8f565/7a33b05099004bccbf5ea334489c40b0/5d226db7dbde402e96c095e89b4945ac/167baf77760640d99d92f20ab4843395
@apiHeader {String} Authorization User's Outh-token

@apiParam {string} courseId course unique Id
@apiParam {string} chapterId chapter unique Id of course
@apiParam {string} sectionId section unique Id of chapter
@apiParam {string} positionId position unique Id (sequenceId) of section
@apiParam {string} componentId component unique Id of position


@apiSuccess {String}  category type of component [html|video|problem|discussion]
@apiSuccess {String}  start start time of section
@apiSuccess {String}  display_name User defined name of component

@apiSuccess {String}  data html contenct of [html] component
@apiSuccess {Boolean}  graded Grading status of [html] component

@apiSuccess {String}  youtube_id_1_25 youtube vedio id of [video] component
@apiSuccess {String}  youtube_id_0_75 youtube vedio id of [video] component
@apiSuccess {String}  youtube_id_1_0 default youtube vedio id of [video] component
@apiSuccess {String}  youtube_id_1_5 youtube vedio id of [video] component
@apiSuccess {String[]}  html5_sources CDN Urls for videos of [video] component
@apiSuccess {Boolean}  download_video download video status of [video] component
@apiSuccess {Boolean}  youtube_is_available youtube status on EDX of [video] component
@apiSuccess {Object[]}  transcript transcript conent of youtube video [video] component
@apiSuccess {String}  start_time custom start time for [video] component
@apiSuccess {String}  end_time custom start time for [video] component


@apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
        "category": "html",
        "start": "2017-05-10T07:00:00Z",
        "display_name": "IFrame Tool",
        "graded": false,
        "data": "<h3 class=\"hd hd-2\">IFrame Tool</h3>\n<p>Use the IFrame tool.</p>"
        }

@apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
        "youtube_id_1_25": "",
        "download_video": true,
        "youtube_is_available": true,
        "html5_sources": [],
        "youtube_id_0_75": "",
        "category": "video",
        "display_name": "Video",
        "transcript": {
                    "start": [
                        260,
                        1510,
                    ],
                    "end": [
                        1510,
                        4480,
                    ],
                    "text": [
                        "ANANT AGARWAL: Welcome to edX. test setest",
                        "I&#39;m Anant Agarwal, I&#39;m the president of edX, test",
                    ]
                },
        "start": "2017-05-10T07:00:00Z",
        "youtube_id_1_0": "3_yD_cEKoCk",
        "end_time": "0.0",
        "youtube_id_1_5": "",
        "start_time": "0.0"
        }
        
@apiUse MyError

"""
@can_disable_rate_limit
class CoursewareIndex(APIView,ApiKeyPermissionMixIn,courseaccess):
    """
        View class for the Courseware page.
    """
    authentication_classes = OAuth2AuthenticationAllowInactiveUser, SessionAuthenticationAllowInactiveUser
    permission_classes = ApiKeyHeaderPermissionIsAuthenticated,
    throttle_classes = EnrollmentUserThrottle,

    @method_decorator(ensure_csrf_cookie_cross_domain)
    @method_decorator(ensure_valid_course_key)

    def get(self, request, course_id, chapter=None, section=None, position=None,component=None):
        self.course_key = CourseKey.from_string(course_id)
        self.request = request
        self.original_chapter_url_name = chapter
        self.original_section_url_name = section
        self.chapter_url_name = chapter
        self.section_url_name = section
        self.position_url_name = position
        self.component_url_name = component
        self.position = position
        self.component = component
        self.chapter, self.section = None, None
        self.url = request.path

        try:
            self._init_new_relic()
            self._get_course_module()
            self.effective_user = self.request.user
            content = self._get()
            return Response(
                status=status.HTTP_200_OK,
                data=content
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
        find all course content's class objects and find user's 
        enrollment to course 
        """
        self._redirect_if_needed_to_access_course()
        self._prefetch_and_bind_course()

        if self.course.has_children_at_depth(CONTENT_DEPTH):
            self.chapter = self._find_chapter()
            if self.chapter is not None:
                self.section = self._find_section()
                if self.section is not None:
                    self.position = self._find_position()
                    self.component = self._find_component()


        return self._create_courseware_context()

    def _create_courseware_context(self):
        """
        return content data for particular component request of course 
         
        """
        table_of_contents = toc_for_course(
            self.effective_user,
            self.request,
            self.course,
            self.chapter_url_name,
            self.section_url_name,
            self.field_data_cache,
        )

        section_context = self._create_section_context(
            table_of_contents['previous_of_active_section'],
            table_of_contents['next_of_active_section'],
        )

        if type(self.component) is unicode or self.component is None:
            raise Http404

        return self._prefetch_component_context(self.component, STUDENT_VIEW, section_context)

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
