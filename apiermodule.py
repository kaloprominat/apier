#!/usr/bin/python
# -*- coding: utf-8 -*-

import bottle, json, datetime

import traceback

class apiermodule(object):

    """base class for constructing modules for apier"""

    __version__ = '0.2.1'

    def __init__(self, **kwargs):
        super(apiermodule, self).__init__()
        
        self.bottleapp = kwargs.get('bottleapp')
        self.active_writelog = kwargs.get('WriteLog')
        self.apier_configs = kwargs.get('configs')

        self.default_result = { 'status' : 0, 'code' : 0, 'data': None, 'message': None }
        self.operational_result = None

        if self.active_writelog == None:
            self.active_writelog = self.local_writelog

        self.BindRoutes()

        self.ResponseType = 'default'


    def __str__(self):
        return '<%s module (apiermodule %s)>' % (self.name, apiermodule.__version__)

    def __repr__(self):
        return self.__str__()

    def WriteLog(self, logstring, loglevel='info', thread=None ):
        if thread == None:
            self.active_writelog(logstring, loglevel, self.name)
        else:
            self.active_writelog(logstring, loglevel, thread)


    def local_writelog(self, logstring, loglevel='info', thread='module' ):

        dt = datetime.datetime.now()

        p_logstring = "%s[%s]: <%s> %s \n" % (dt.strftime("%Y-%m-%d %H:%M:%S"), loglevel.upper(), thread, logstring )

        print p_logstring

    def ProccessRoute(self, **kwargs):
        
        Request = self.ParseRequest(kwargs)
        Response = None

        self.operational_result = self.default_result.copy()

        AnswerOptions = {
            'ResponseType' : 'default',
            'ResponseData' : {},
            'ResponseHeader' : {}
        }

        try:
            Response = self.routes[Request['matched_route']]['function'](Request, options=AnswerOptions)
            result = self.operational_result
        except Exception as e:
            result = self.operational_result
            result['status'] = 1
            result['code'] = 1
            result['data'] = None
            result['message'] = "Unhandled error '%s' in module function %s" % (e, self.routes[Request['matched_route']]['function'])
            self.WriteLog("%s %s: Unhandled error '%s' in module function %s" % ( Request['bottle.request'].method,Request['matched_route'] , e, self.routes[Request['matched_route']]['function']), 'error', self.name)
            self.WriteLog('%s' % traceback.format_exc(e), 'error', self.name )
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
            self.WriteLog('%s' % traceback.format_exc(e), 'error', self.name )

        if AnswerOptions['ResponseType'] == 'default':
            return result
        else:
            return result['data']

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

        # if bottle.request.has_key('route.handle'):
        data['matched_route'] = bottle.request['route.handle'].rule
        data['matched_route_method'] = bottle.request['route.handle'].method
        # else:
            # data['matched_route'] = bottle.request.route.rule
            # data['matched_route_method'] = bottle.request.route.method

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

    def ModifyResponseData(self, parametrs):

        response_data = self.operational_result
        for item in parametrs:
            response_data[item] = parametrs[item]

    def SetResposeTypeCustom(self):

        self.ResponseType = 'custom'

    def SetResponseTypeDefault(self):

        self.ResponseType = 'default'


