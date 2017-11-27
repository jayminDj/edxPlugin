

class Http401(Exception):
   """Base class for other exceptions"""
   def __init__(self, *args):
        # *args is used to get a list of the parameters passed in
        self.args = [a for a in args]
