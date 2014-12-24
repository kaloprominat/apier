#!/usr/bin/python
# -*- coding: utf-8 -*-

from apiermodule import apiermodule

name = 'example2'

routes = {
        '/test2'    :   {'method'   :   'GET' },
        '/test2/'   :   {'method'   :   'POST'},
        '/test2/<name>'   :   {'method'   :   'ANY'}
    
        }

class apimodule(apiermodule):

    """docstring for apimodule"""

    def __init__(self, **kwargs):

        self.name = name
        self.routes = routes

        self.routes['/test2']['function'] = self.func1
        self.routes['/test2/']['function'] = self.func1
        self.routes['/test2/<name>']['function'] = self.func2

        super(apimodule, apimodule).__init__(self, **kwargs)

    def func1(self, Request):

        Request['bottle.request'] = None
        Request['bottle.response'] = None

        return Request

    def func2(self, Request):

        if Request['variables']['name'] == 'specialname':
            self.ModifyResponseHeader({'status':201})

        return 'OK: 201 created'

if __name__ == '__main__':

    import bottle

    bottle.debug(True)

    bottleapp = bottle.Bottle()

    module = apimodule(bottleapp=bottleapp)

    bottle.run(app=bottleapp, host='0.0.0.0', port='8080', server='paste')

