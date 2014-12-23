#!/usr/bin/python
# -*- coding: utf-8 -*-

from apiermodule import apiermodule

name = 'example1'
routes = {
        '/test1'    :   {'method'   :   'GET' },
        '/test1/'   :   {'method'   :   'POST'},
        '/test1/<name>'   :   {'method'   :   'ANY'}
    
        }


class apimodule(apiermodule):
    """docstring for apimodule"""

    def __init__(self, **kwargs):

        self.name = name
        self.routes = routes


        self.routes['/test1']['function'] = self.func1
        self.routes['/test1/']['function'] = self.func1
        # self.routes['/test1/<name>']['function'] = self.func2
        self.routes['/test1/<name>']['function'] = 123
        


        super(apimodule, apimodule).__init__(self, **kwargs)


        

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
    import bottle
    bottleapp = bottle.Bottle()
    module = apimodule(bottleapp=bottleapp, WriteLog=None)

    bottleapp.run(host='0.0.0.0', port='8080', debug=True, server='paste')

