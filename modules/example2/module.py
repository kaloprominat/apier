#!/usr/bin/python
# -*- coding: utf-8 -*-

from apiermodule import apiermodule

name = 'example2'
routes = {
        '/test2'    :   {'method'   :   'POST' },
        '/test2/'   :   {'method'   :   'GET'},
        '/test2/<name>'   :   {'method'   :   'ANY'}
    
        }


class apimodule(apiermodule):
    """docstring for apimodule"""

    def __init__(self, bottleapp=None, WriteLog=None):

        self.WriteLog = WriteLog

        super(apimodule, apimodule).__init__(self, bottleapp)

        self.name = name
        self.routes = routes

        self.bottleapp = bottleapp

        self.routes['/test2']['function'] = self.func1
        self.routes['/test2/']['function'] = self.func2
        self.routes['/test2/<name>']['function'] = self.func2
        # self.routes['/test2/<name>']['function'] = 123

        self.BindRoutes()

    def func2(self, Request):

        if Request['variables']['name'] == 'suka':
            self.ModifyResponseHeader({'status':201})

        return 'pp[a'

    def func1(self, Request):

        # Request['bottle.request'] = None
        # Request['bottle.response'] = None

        # a = 1 / 0

        return Request

if __name__ == '__main__':
    pass    
