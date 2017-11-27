"""
X_module for pural-plugin is extends package of xmodule.x_module

"""
from .sequence_module import SequenceModuleContext
from .component_module import ComponentModuleConext
from  xmodule.x_module import (
    CombinedSystem,
    MetricsMixin,
    PREVIEW_VIEWS,
    STUDENT_VIEW,
    AUTHOR_VIEW,
    STUDIO_VIEW
)
from xblock.exceptions import (
    NoSuchViewError,
    NoSuchHandlerError,
    NoSuchServiceError,
    NoSuchUsage,
    NoSuchDefinition,
    FieldDataDeprecationWarning,
)



class CombinedSystemContext(CombinedSystem):

    def __init__(self,module_system, descriptor_system):
        super(CombinedSystemContext,self).__init__(module_system,descriptor_system)


    def render_sequense_context(self, block, view_name, context=None):
        """
        
        :param block: object
        :param view_name: string
        :param context: dict
        :return: dict
        """
        context = context or {}
        if view_name in PREVIEW_VIEWS:
            block = self._get_student_block(block)

        sequence_module = SequenceModuleContext(block)

        view_fn = getattr(sequence_module, view_name, None)
        if view_fn is None:
            raise NoSuchViewError(sequence_module, view_name)

        frag = view_fn(sequence_module._sequenceModule,context)

        return frag

    def render_component_context(self,component,view_name,context=None):
        """
                :param component: object
                :param view_name: string
                :param context: dict
                :return: dict
        """

        context = context or {}
        if view_name in PREVIEW_VIEWS:
            block = self._get_student_block(component)

        component_module = ComponentModuleConext(component)

        view_fn = getattr(component_module, view_name, None)
        if view_fn is None:
            raise NoSuchViewError(component_module, view_name)

        frag = view_fn(component_module._component._xmodule, context)

        return frag








