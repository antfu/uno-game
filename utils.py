# -*- coding: utf-8 -*-
# @Author: Anthony
# @Date:   2016-04-03 01:48:03
# @Last Modified by:   Anthony
# @Last Modified time: 2016-04-04 13:32:29

import threading

def name_prettify(name):
    return ' '.join([x.capitalize() for x in name.replace('_',' ').split(' ')])
def name_normalize(name):
    return name.lower().replace(' ','_')

def set_timeout(func, sec):
    t = None
    def func_wrapper():
        func()
        t.cancel()
    t = threading.Timer(sec, func_wrapper)
    t.start()
    return t

class NoneGet:
    def __init__(self, error=None, readable=None):
        self.error = error
        self.readable = readable

    def __bool__(self):
        return False

    def __repr__(self):
        if not self.error is None:
            return str(self.error)
        else:
            return 'no_default_error'

    def __str__(self):
        if not self.readable is None:
            return str(self.readable)
        else:
            return repr(self)