# -*- coding: utf-8 -*-


class Error(Exception):
    """all captain errors will inherit from this base class"""
    pass


class Stop(Error):
    """This will stop execution and return the given code

    :Example:
        raise StopError(2, "this is the message")
    """
    def __init__(self, code, msg="", *args, **kwargs):
        """create the error

        :param code: integer, the exit code
        :param msg: string, the message will be printed out to stderr if
            code!=0 or stdout if code==0
        """
        self.code = code
        super().__init__(msg, *args, **kwargs)

