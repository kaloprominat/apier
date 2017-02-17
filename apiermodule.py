#!/usr/bin/python
# -*- coding: utf-8 -*-

import bottle
import json
import datetime
import logging
import traceback

from xml.dom.minidom import Document


class apiermoduleException(Exception):
    """docstring for apiermoduleException"""
    def __init__(self, **kwargs):
        super(apiermoduleException, self).__init__()
        for item in kwargs:
            self.__setattr__(item, kwargs[item])

    def __str__(self):
        s = ''
        for attr, value in self.__dict__.iteritems():
            s += '%s: %s\n' % (attr, value)
        return s


class apiermodule(object):

    """base class for constructing modules for apier"""

    __version__ = '1.0.1'

    def __init__(self, **kwargs):

        super(apiermodule, self).__init__()

        self.name = 'apiermodule'

        self.bottleapp = kwargs.get('bottleapp')
        self.apier_configs = kwargs.get('configs')

        self.loglevel = kwargs.get('loglevel', logging.DEBUG)
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.loglevel)

        self.return_handler = self.JsonStatusReturner
        self.error_handler = self._Returner

        # self.BindRoutes()
    def after_init(self):

        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.loglevel)

        self.BindRoutes()

    # returners functions

    def _Return_res(self):
        response = {
            'body': '',
            'http_headers' : {},
            'http_code' : 200
        }
        return response

    def Error(self, **kwargs):
        if hasattr(self.error_handler, '__call__'):
            return self.error_handler(**kwargs)
        else:
            return self._Returner(**kwargs)

    def _Returner(self, **kwargs):

        kwargs['response'] = kwargs.get('response', self._Return_res())
        return self.return_handler(**kwargs)

    def BasicReturner(self, **kwargs):

        res = kwargs.get('response')

        data = kwargs.get('data', None)
        err = kwargs.get('error', None)

        if err is not None:
            res['body'] = err if type(err) == apiermoduleException else traceback.format_exc(err)
            res['http_code'] = 500
        else:
            res['body'] = data

        res['body'] = res['body'].__str__()

        return res

    def JsonReturner(self, **kwargs):


        res = kwargs.get('response')

        data = kwargs.get('data', None)
        err = kwargs.get('error', None)

        res['http_headers'].update({'Content-Type': 'application/json'})

        if err is not None:
            res['body'] = { 'exception' : err.__dict__ if type(err) == apiermoduleException else traceback.format_exc(err) }
            res['http_code'] = 500
        else:
            res['body'] = data
            

        res['body'] = json.dumps(res['body'])
        return res

    def JsonStatusReturner(self, **kwargs):

        res = kwargs.get('response')

        data = kwargs.get('data', None)
        err = kwargs.get('error', None)

        res['http_headers'].update({'Content-Type': 'application/json'})
        res['body'] = {
            'status'    : 0,
            'code'      : 0,
            'data'      : data
        }

        if err is not None:
            res['body']['status'] = 1
            for attr, value in err.__dict__.iteritems():
                res['body'][attr] = value

        res['body'] = json.dumps(res['body'])

        return res


    def XmlReturner(self, **kwargs):

        res = kwargs.get('response')

        data = kwargs.get('data', None)
        err = kwargs.get('error', None)

        res['http_headers'].update({'Content-Type': 'application/xml'})

        def _xml_from_data(data):

            doc = Document()

            def build(father, structure):
                if type(structure) == dict:

                    for k in structure:
                        tag = doc.createElement(str(k))
                        father.appendChild(tag)
                        build(tag, structure[k])

                elif type(structure) == list:
                    grandFather = father.parentNode
                    tagName = str(father.tagName)
                    grandFather.removeChild(father)
                    for l in structure:
                        tag = doc.createElement(tagName)
                        build(tag, l)
                        grandFather.appendChild(tag)

                else:
                    data = str(structure)
                    tag = doc.createTextNode(data)
                    father.appendChild(tag)

            if len(data) == 1:
                rootName = str(data.keys()[0])
                root = doc.createElement(rootName)

                doc.appendChild(root)
                build(root, data[rootName])

            return doc.toprettyxml(indent="  ")

        if err is None:
            res['body'] = _xml_from_data({'data': data})
        else:
            res['body'] = _xml_from_data({'error': err.__dict__})
            res['http_code'] = 500

        return res

    def __str__(self):
        return '<%s (apiermodule %s) at %s>' % (self.name, apiermodule.__version__, hex(id(self)))

    def __repr__(self):
        return self.__str__()

    def WriteLog(self, logstring, loglevel='info', thread=None ):
        self.logger.__getattribute__(loglevel)(logstring)

    def ProccessRoute(self, **kwargs):

        Request = self.ParseRequest(kwargs)

        response = self._Return_res()

        try:
            data = self.routes[Request['matched_route']]['function'](Request, response=response)
        except Exception, e:
            ret_data = self.Error(error=e, response=response)            
        else:
            ret_data = self._Returner(data=data, response=response)


        # applying response

        for header in ret_data['http_headers']:
            bottle.response.set_header(header, ret_data['http_headers'][header])

        bottle.response.status = ret_data['http_code']

        self.WriteLog(ret_data,'debug')

        return ret_data['body']

    # def ProccessRoute2(self, **kwargs):
        

    #     Request = self.ParseRequest(kwargs)
    #     Response = None

    #     self.operational_result = self.default_result.copy()

    #     AnswerOptions = {
    #         'ResponseType' : 'default',
    #         'ResponseData' : {},
    #         'ResponseHeader' : {}
    #     }

    #     try:
    #         Response = self.routes[Request['matched_route']]['function'](Request, options=AnswerOptions)
    #         result = self.operational_result
    #     except Exception as e:
    #         result = self.operational_result
    #         result['status'] = 1
    #         result['code'] = 1
    #         result['data'] = None
    #         result['message'] = "Unhandled error '%s' in module function %s" % (e, self.routes[Request['matched_route']]['function'])
    #         self.WriteLog("%s %s: Unhandled error '%s' in module function %s" % ( Request['bottle.request'].method,Request['matched_route'] , e, self.routes[Request['matched_route']]['function']), 'error', self.name)
    #         self.WriteLog('%s' % traceback.format_exc(e), 'error', self.name )
    #     else:
    #         result['data'] = Response

    #     try:
    #         # json.dumps(Response)
    #         self.returner_function(Response)
    #     except Exception as e:
    #         result['status'] = 1
    #         result['code'] = 2
    #         result['data'] = None
    #         result['message'] = 'Module function %s returned unserializable data: \'%s\'' % (self.routes[Request['matched_route']]['function'], e)

    #         self.WriteLog("%s %s: Module function %s returned unserializable data: '%s'" % ( Request['bottle.request'].method, Request['matched_route'] , self.routes[Request['matched_route']]['function'],e), 'error', self.name)
    #         self.WriteLog('%s' % traceback.format_exc(e), 'error', self.name )

    #     if AnswerOptions['ResponseType'] == 'default':
    #         return result
    #     else:
    #         return result['data']

    def BindRoutes(self):

        added_routes = {}

        for route in self.routes:
            if not hasattr(self.routes[route]['function'], '__call__'):
                self.WriteLog('Function variable for route %s is not actually callable: %s' % (route, self.routes[route]['function']), 'warn', self.name)
            if hasattr(self, 'base_url'):
                f_route = '%s/%s' % (self.base_url, route)
                f_route = f_route.replace('//','/')
                added_routes.update({f_route: self.routes[route]})
            else:
                f_route = route
            self.bottleapp.route(f_route, method=self.routes[route]['method'])(self.ProccessRoute)
            self.WriteLog('Binded route %s with method %s to function %s' % (f_route, self.routes[route]['method'], self.routes[route]['function']), 'debug', self.name)

        self.routes.update(added_routes)

    def ParseRequest(self, kwargs):

        data = {
                "bottle.request": bottle.request,
                "bottle.response": bottle.response,
                "http_headers":{},
                "get": {},
                "post": {},
                "path": None,
                "matched_route" : None,
                "matched_route_method" : None,
                "variables": kwargs,
                "body" : None
                }
        data['path'] = bottle.request.path

        data['matched_route'] = bottle.request['route.handle'].rule
        data['matched_route_method'] = bottle.request['route.handle'].method

        data['body'] = bottle.request.body.read()


        for header in bottle.request.headers:
            data['http_headers'].update({header: bottle.request.headers[header]})

        for getitem in bottle.request.query:
            data['get'].update({getitem: bottle.request.query.get(getitem)})


        for postitem in bottle.request.POST:
            data['post'].update({postitem: bottle.request.POST.get(postitem)})

        return data

    # def ModifyResponseHeader(self, parametrs):
        
    #     response = bottle.response

    #     if parametrs.has_key('headers'):
    #         for header in parametrs['headers']:
    #             if header[0] == 'Content-Type':
    #                 response.content_type = header[1]
    #             response.set_header(header[0], header[1])
    #     if parametrs.has_key('status'):
    #         response.status = parametrs['status']



