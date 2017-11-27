"""
sequence_module for pural-plugin

"""
import datetime
from  xmodule.x_module import (
    CombinedSystem,
    MetricsMixin,
    PREVIEW_VIEWS,
    STUDENT_VIEW,
    AUTHOR_VIEW,
    STUDIO_VIEW
)
from .vertical_block import VerticalBlockContext
from xblock.exceptions import (
    NoSuchViewError,
    NoSuchHandlerError,
    NoSuchServiceError,
    NoSuchUsage,
    NoSuchDefinition,
    FieldDataDeprecationWarning,
)


"""
SequenceModuleContext creates new object and extend funcationality of xblock.internal.SequenceModuleWithMixins 

"""
class SequenceModuleContext(object):

    def __new__(cls,_sequenceModule):
        instance = super(SequenceModuleContext, cls).__new__(cls)
        instance.__init__(_sequenceModule)
        return instance

    def __init__(self,_sequenceModule):
        self._sequenceModule = _sequenceModule

    def student_view(self, _sequenceModule, context):
        context = context or {}
        _sequenceModule._capture_basic_metrics()
        banner_text = None

        """
        fetch list of sequence items in section
        """
        display_items = _sequenceModule.get_display_items()
        context_data = []

        for item in display_items:
            if item is not None:

                if item.start.date() <= datetime.date.today():
                    if item.has_children:
                        sequence_access = sequenceaccess()
                        """
                        fetch all child context of sequcence item.
                        
                        """
                        child_context = sequence_access._prefetch_sequence_child_context(item,STUDENT_VIEW,context)

                data = {
                    'category':item.category,
                    'display_name':item.display_name,
                    'display_name_with_default_escaped':item.display_name_with_default_escaped,
                    'graded':item.graded,
                    'has_children':item.has_children,
                    'url_name':item.url_name,
                    'has_score':item.has_score,
                    'showanswer':item.showanswer,
                    'start':item.start,
                    'is_entrance_exam':item.is_entrance_exam
                }

                if child_context is not None:
                    data['childrens'] = child_context
                context_data.append(data)


        return context_data


class sequenceaccess:

    def __init__(self):
        self = self

    def _prefetch_sequence_child_context(self, sequence, view_name, context):

       combinedContext  = sequenceCombinedSystemContext(sequence.xmodule_runtime,sequence._runtime)
       return combinedContext.render_sequense_child_context(sequence,view_name, context)


"""
Class sequenceCombinedSystemContext extends class CombinedSystem of package xmodule.x_module

"""
class sequenceCombinedSystemContext(CombinedSystem):

    def __init__(self, module_system, descriptor_system):
        super(sequenceCombinedSystemContext, self).__init__(module_system, descriptor_system)


    def render_sequense_child_context(self, block, view_name, context=None):

        """ 
            :param block: object
            :param view_name: string
            :param context: dict
            :return: dict
        """
        context = context or {}
        if view_name in PREVIEW_VIEWS:
            block = self._get_student_block(block)

        vertical_block = VerticalBlockContext(block)

        view_fn = getattr(vertical_block, view_name, None)
        if view_fn is None:
            raise NoSuchViewError(vertical_block, view_name)

        frag = view_fn(vertical_block._verticalBlock, context)

        return frag