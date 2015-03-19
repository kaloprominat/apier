#!/usr/bin/python
# -*- coding: utf-8 -*-

#   Importing apiermodule to be userd as BASECLASS

from apiermodule import apiermodule

#   Giving name for our python module

name = 'example1'

#   Describing routes, which our apimodule will process
#
#   dict = { '<route_path>': { 'method': '<http_method>' }, ... }

routes = {
        '/test1'    :   {'method'   :   'GET' },
        '/test1/'   :   {'method'   :   'POST'},
        '/test1/<name>'   :   {'method'   :   'ANY'}
    
        }

# Constructing our apimodule class

class apimodule(apiermodule):

    """docstring for apimodule"""

    #   Overriding __init__ baseclass function

    def __init__(self, **kwargs):


        #   There we should set name and routes for our class instance

        self.name = name
        self.routes = routes


        #   And there we shoud map all routes to functions, which will be processing requests

        self.routes['/test1']['function'] = self.func1
        self.routes['/test1/']['function'] = self.func1

        #   Pay some attention on this part
        #   You are able to use bottle-style variables at path, like /api/object/<name>
        #   and variable will be served in Request object to function func2

        self.routes['/test1/<name>']['function'] = self.func2

        #   Finnaly, we should initialize baseclass object

        super(apimodule, apimodule).__init__(self, **kwargs)

        #   After that, we have available configs variable

        self.configs = self.apier_configs

        self.WriteLog('configs: %s' % self.configs.__str__(), 'info', self.name)

    #   First function func1 process requests for first to paths /test1 and /test1/
    #   baseclass apiermodule passes Request dict to function with all request data
    #
    #   This function simply returns all request object to be presented as api answer
    #

    def func1(self, Request):

        #   
        #   Request dict structure example for POST request by url /test1/testname?opa=1:
        #
        #   {
        #     "bottle.response": <bottle.response object>,  for low-level access and inner baseclass logic
        #
        #     "matched_route_method": "GET",                HTTP method, that was used
        #
        #     "bottle.request": <bottle.request object>,    for low-level access and inner baseclass logic
        #
        #     "post_body": "form2=form",                    the body of POST data request, if there was one
        #
        #     "http_headers": [                             all HTTP headers, that were sent from client
        #         {
        #             "Content-Length": "0"
        #         },
        #         {
        #             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.120 Safari/537.36"
        #         },
        #         {
        #             "Connection": "keep-alive"
        #         },
        #         {
        #             "Host": "127.0.0.1:8080"
        #         },
        #         {
        #             "Cache-Control": "no-cache"
        #         },
        #         {
        #             "Accept": "application/xml, text/xml, */*; q=0.01"
        #         },
        #         {
        #             "Accept-Language": "en-US,en;q=0.8,ru;q=0.6"
        #         },
        #         {
        #             "Content-Type": "application/xml, text/xml, */*; q=0.01, application/x-www-form-urlencoded"
        #         },
        #         {
        #             "Accept-Encoding": "gzip,deflate,sdch"
        #         }
        #     ],
        #     "path": "/test1/testname",                    http path, that was requested
        #
        #     "post": [{                                    post form variables will be stored as dicts in list
        #           "form2": "form"
        #               }],
        #  
        #     "get": [{                                     get variables will be stored as dicts in list
        #        "opa": "1"
        #             }],
        #
        #     "variables": {                                bottle path variables will be stored here as dict
        #               "name" : "testname"
        #                   },
        #
        #     "matched_route": "/test1/<name>"              matched module route
        #   }


        #   Request data structure contains <bottle.* > object, which actually can not be serialized as json to be served as api answer
        #   and it will generate api error
        #
        #   so here we striping them from returned variable

        Request['bottle.request'] = None
        Request['bottle.response'] = None


        return Request

        #   HTTP response will be:
        #
        #   http status: 200
        #
        #   http body:
        #
        #   {
        #       "status": 0,
        #       "message": null,
        #       "code": 0,
        #       "data": <Request dict>
        #   }


    #   Function func2 shows how to modify answer HTTP header, if needed

    def func2(self, Request):

        #   If some conditions met some requirements, we can change HTTP status code to some other needed
        #  
        #   For that, we call self.ModifyResponseHeader and pass to in dict with modifications

        #   It can contain {'status': <code number>, 'headers': [('Content-Type', 'application/json'), ('...','...'), ...] }
        #   headers - is a list, containing tuples of header - value for http response.

        if Request['variables']['name'] == 'specialname':
            self.ModifyResponseHeader({'status':201})

        return 'OK: 201 created'

        #   Http response will be:
        #
        #   http status 201
        #   
        #   http body:
        #
        #   {
        #       "status": 0,
        #       "message": null,
        #       "code": 0,
        #       "data": "OK: 201 created"
        #   }


#   Last part is making module suitable for running standalone, without apier daemon

#   This condition satisfies when module executed like "python module.py"

if __name__ == '__main__':
    
    #   Importing bottle, to create standalone application

    import bottle

    #   Turning on debug

    bottle.debug(True)

    bottleapp = bottle.Bottle()

    #   Initializing module and pass to it bottle application and 

    module = apimodule(bottleapp=bottleapp)

    #   Run application

    bottle.run(app=bottleapp, host='0.0.0.0', port='8080', server='paste')


#   That's all. Clear module example without commentary you may find in example2 module


