# -*- coding: utf-8 -*-


class MegaException(Exception):
    pass
    
class MegaIncorrectPasswordExcetion(MegaException):
    """
    A incorrect password or email was given.
    """

class MegaRequestException(MegaException):
    """
    There was an error in the request.
    """
    pass
