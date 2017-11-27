"""
vertical_block for pural-plugin 

"""

from copy import copy

class VerticalBlockContext(object):

    def __new__(cls,_verticalBlock):
        instance = super(VerticalBlockContext, cls).__new__(cls)
        instance.__init__(_verticalBlock)
        return instance

    def __init__(self,_verticalBlock):
        self._verticalBlock = _verticalBlock

    def student_view(self, _verticalBlock, context):
        """
        Renders the student view of the block in the section context.
        """
        contents = []
        if context:
            child_context = copy(context)
        else:
            child_context = {}

        context_data = []
        for child in _verticalBlock.get_display_items():
            if child is not None:
                data = {
                    'display_name' : child.display_name,
                    'display_name_with_default_escaped' : child.display_name_with_default_escaped,
                    'url_name':child.url_name,
                    'category':child.category
                }
                context_data.append(data)

        return context_data

