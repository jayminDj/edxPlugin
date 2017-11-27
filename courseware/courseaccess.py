"""
Courseaccess for pural-pugin

"""

import logging
import newrelic.agent
from django.http import Http404
from xmodule.modulestore.django import modulestore
from courseware.courses import get_studio_url, get_course_with_access
from courseware.access import has_access, _adjust_start_date_for_beta_testers
from courseware.model_data import FieldDataCache
from courseware.module_render import toc_for_course, get_module_for_descriptor
from courseware.views.views import get_current_child, registered_for_course
from django.http import Http404
from student.roles import GlobalStaff
from student.models import CourseEnrollment
from courseware.url_helpers import get_redirect_url_for_global_staff
from courseware.exceptions import Redirect
from rest_framework import status
from rest_framework.response import Response
from ..exceptions import Http401
from ..lib.x_module import CombinedSystemContext

CONTENT_DEPTH = 2
log = logging.getLogger("plugin.courseware.courseacess")

class courseaccess:

    def __init__(self):
        self = self

    def _init_new_relic(self):
        """
        Initialize metrics for New Relic so we can slice data in New Relic Insights
        """
        newrelic.agent.add_custom_parameter('course_id', unicode(self.course_key))
        newrelic.agent.add_custom_parameter('org', unicode(self.course_key.org))

    def _get_course_module(self):
        with modulestore().bulk_operations(self.course_key):
            self.course = get_course_with_access(self.request.user, 'load', self.course_key, depth=CONTENT_DEPTH)
            self.is_staff = has_access(self.request.user, 'staff', self.course)

    def _prefetch_and_bind_course(self):
        """
        Prefetches all descendant data for the requested section and
        sets up the runtime, which binds the request user to the section.
        """
        self.field_data_cache = FieldDataCache.cache_for_descriptor_descendents(
            self.course_key, self.effective_user, self.course, depth=CONTENT_DEPTH,
        )

        self.course = get_module_for_descriptor(
            self.effective_user,
            self.request,
            self.course,
            self.field_data_cache,
            self.course_key,
            course=self.course,
        )

    def _find_block(self, parent, url_name, block_type, min_depth=None):
        """
        Finds the block in the parent with the specified url_name.
        If not found, calls get_current_child on the parent.
        """
        child = None
        if url_name:
            child = parent.get_child_by(lambda m: m.location.name == url_name)
            if not child:
                # User may be trying to access a child that isn't live yet
                if not self._is_masquerading_as_student():
                    raise Http404('No {block_type} found with name {url_name}'.format(
                        block_type=block_type,
                        url_name=url_name,
                    ))
            elif min_depth and not child.has_children_at_depth(min_depth - 1):
                child = None
        if not child:
            child = get_current_child(parent, min_depth=min_depth, requested_child=self.request.GET.get("child"))
        return child


    def _find_chapter(self):
        """
        Finds the requested chapter.
        """
        return self._find_block(self.course, self.chapter_url_name, 'chapter', CONTENT_DEPTH - 1)

    def _find_section(self):
        """
        Finds the requested section.
        """
        if self.chapter:
            return self._find_block(self.chapter, self.section_url_name, 'section')

    def _find_position(self):
        """
        Finds the requested section.
        """
        if self.section:
            return self._find_block(self.section, self.position_url_name, 'position')

    def _find_component(self):
        """
        Finds the requested section.
        """
        if self.position:
            return self._find_block(self.position, self.component_url_name, 'component')

    def _prefetch_and_bind_section(self):
        """
        Prefetches all descendant data for the requested section and
        sets up the runtime, which binds the request user to the section.
        """
        # Pre-fetch all descendant data
        self.section = modulestore().get_item(self.section.location, depth=None, lazy=False)
        self.field_data_cache.add_descriptor_descendents(self.section, depth=None)

        # Bind section to user
        self.section = get_module_for_descriptor(
            self.effective_user,
            self.request,
            self.section,
            self.field_data_cache,
            self.course_key,
            self.position,
            course=self.course,
        )

    def _redirect_if_needed_to_access_course(self):
        """
        Verifies that the user can enter the course.
        """
        self._redirect_if_needed_to_register()

    def _redirect_if_needed_to_register(self):
        """
        Verify that the user is registered in the course.
        """
        if not registered_for_course(self.course, self.effective_user):
            log.debug(
                u'User %s tried to view course %s but is not enrolled',
                self.effective_user,
                unicode(self.course.id)
            )
            raise Http401("User must enroll to course.")


    def _prefetch_sequence_context(self, section, view_name, context):
        """
        :param : section (object)
        :param : view_name (string)
        :param : context (dict)
        :return : Context (dict)
        """
        combinedContext  = CombinedSystemContext(section.xmodule_runtime,section._runtime)
        return combinedContext.render_sequense_context(section,view_name, context)

    def _prefetch_component_context(self, component, view_name, context):
        """
        :param : componet (object)
        :param : view_name (string)
        :param : context (dict)
        :return : Context (dict)
        """
        combinedContext  = CombinedSystemContext(component.xmodule_runtime,component._runtime)
        return combinedContext.render_component_context(component,view_name, context)


