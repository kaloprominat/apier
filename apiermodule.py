#!/usr/bin/python
# -*- coding: utf-8 -*-

import bottle, json

class apiermodule(object):

    """base class for constructing modules for apier"""

    def __init__(self, bottleapp):
        super(apiermodule, self).__init__()
        self.bottleapp = bottleapp

    def ProccessRoute(self, **kwargs):
        
        Request = self.ParseRequest(kwargs)
        Response = None

        result = { 'status' : 0, 'code' : 0, 'data': None, 'message': None }

        try:
            Response = self.routes[Request['matched_route']]['function'](Request)
        except Exception as e:
            result['status'] = 1
            result['code'] = 1
            result['data'] = None
            result['message'] = "Unhandled error '%s' in module function %s" % (e, self.routes[Request['matched_route']]['function'])
            self.WriteLog("%s %s: Unhandled error '%s' in module function %s" % ( Request['bottle.request'].method,Request['matched_route'] , e, self.routes[Request['matched_route']]['function']), 'error', self.name)
        else:
            result['data'] = Response

        try:
            json.dumps(Response)
        except Exception as e:
            result['status'] = 1
            result['code'] = 2
            result['data'] = None
            result['message'] = 'Module function %s returned unserializable data: \'%s\'' % (self.routes[Request['matched_route']]['function'], e)

            self.WriteLog("%s %s: Module function %s returned unserializable data: '%s'" % ( Request['bottle.request'].method, Request['matched_route'] , self.routes[Request['matched_route']]['function'],e), 'error', self.name)


        return result

    def BindRoutes(self):
        for route in self.routes:
            if not hasattr(self.routes[route]['function'], '__call__'):
                self.WriteLog('Function variable for route %s is not actually callable: %s' % (route, self.routes[route]['function']), 'warn', self.name)
            self.bottleapp.route(route, method=self.routes[route]['method'])(self.ProccessRoute)
            self.WriteLog('Binded route %s with method %s to function %s' % (route, self.routes[route]['method'], self.routes[route]['function']), 'debug', self.name)

    def ParseRequest(self, kwargs):
        data = {
                "bottle.request": bottle.request,
                "bottle.response": bottle.response,
                "http_headers":[],
                "get": [],
                "post": [],
                "path": None,
                "matched_route" : None,
                "matched_route_method" : None,
                "variables": kwargs,
                "post_body" : None
                }
        data['path'] = bottle.request.path
        data['matched_route'] = bottle.request.route.rule
        data['matched_route_method'] = bottle.request.route.method

        for header in bottle.request.headers:
            data['http_headers'].append({header:bottle.request.headers[header]})

        for getitem in bottle.request.query:
            data['get'].append({getitem: bottle.request.query.get(getitem)})

        data['post_body'] = bottle.request.body.read()

        for postitem in bottle.request.POST:
            data['post'].append({postitem:bottle.request.POST.get(postitem)})

        return data

    def ModifyResponseHeader(self, parametrs):
        
        response = bottle.response

        if parametrs.has_key('headers'):
            for header in parametrs['headers']:
                if header[0] == 'Content-Type':
                    response.content_type = header[1]
                response.set_header(header[0], header[1])
        if parametrs.has_key('status'):
            response.status = parametrs['status']


