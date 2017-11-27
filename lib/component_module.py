"""
component_module for pural-plugin

"""

from xmodule.html_module import HtmlModuleMixin
from xmodule.video_module.video_module import VideoModule
from xmodule.video_module.transcripts_utils import Transcript
import json

class ComponentModuleConext(object):

    def __new__(cls,_component):
        instance = super(ComponentModuleConext, cls).__new__(cls)
        instance.__init__(_component)
        return instance

    def __init__(self,_component):
        self._component = _component


    def student_view(self, _component, context):
        """
        Renders the student view for the component content.
        """
        self._component = _component
        if(isinstance(self._component,HtmlModuleMixin)):
            return self.get_html_module_content()
        elif(isinstance(self._component,VideoModule)):
            return self.get_vedio_module_conent()
        else:
            return {}


    def get_html_module_content(self):
        """
        provide the content data for HTML component.
        :return: dict 
        """

        content = {
            'start' : self._component.start,
            'display_name' : self._component.display_name,
            'graded' : self._component.graded,
            'category' : self._component.category,
            'data' :  self._component.data
        }

        return content

    def get_vedio_module_conent(self):
        """
        Provide the content data for Video component.
        :return: dict 
        """
        content = {
            'category' : self._component.category,
            'start': self._component.start,
            'display_name': self._component.display_name,
            'youtube_is_available' : self._component.youtube_is_available,
            'youtube_id_0_75' : self._component.youtube_id_0_75,
            'youtube_id_1_0' : self._component.youtube_id_1_0,
            'youtube_id_1_25' : self._component.youtube_id_1_25,
            'youtube_id_1_5' : self._component.youtube_id_1_5,
            'start_time' : self._component.start_time,
            'end_time' : self._component.end_time,
            'download_video' : self._component.download_video,
        }

        if self._component.html5_sources is not None:
            temp_source = []
            for key in self._component.html5_sources:
                temp_source.append({'url':key})
            content['html5_sources'] = temp_source

        transcript_info = self._component.get_transcripts_info()
        if len(transcript_info['sub']) is not 0:
            transcript = Transcript()
            transcript_content = transcript.asset(self._component.location,transcript_info['sub'])
            content['transcript'] = json.loads(transcript_content.data)

        return content

