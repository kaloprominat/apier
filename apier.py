#!/usr/bin/python
# -*- coding: utf-8 -*-

import bottle, ConfigParser, sys, thread, imp, os, json, datetime, signal, hashlib

#   This hack is for disabling reverse DNS lookups

__import__('BaseHTTPServer').BaseHTTPRequestHandler.address_string = lambda x:x.client_address[0]


from threading import Thread
from optparse import OptionParser


PARSER = OptionParser()

PARSER.add_option('-c', '--config', dest='configfile',
                        help='configuration file path',
                        default='/etc/caspersuite-licenses-daemon/daemon.conf'
                        )
PARSER.add_option('-t', '--test-config', dest='testconfig',
                        help='do not run, just test specified config',
                        action='store_true'
                        )

PARSER.add_option('-f', '--foreground', dest='foreground',
                        help='run in silent mode, only errors will be reported',
                        action='store_true'
                        )

OPTIONS, ARGS = PARSER.parse_args()

CONFIGFILE = OPTIONS.configfile

CONFIG = ConfigParser.RawConfigParser(allow_no_value=True)

LOGLEVELS = {
    "silent"    : 0,
    "error"     : 1,
    "warn"      : 2,
    "info"      : 3,
    "debug"     : 4
}


LOGLEVEL = LOGLEVELS['debug']

HASHER = hashlib.md5()


try:
    CONFIG.read(CONFIGFILE)
except Exception, e:
    print '[ERR] Error loading config file: %s' % e
    sys.exit(1)

try:

    BINDIP=CONFIG.get('daemon', 'bindip')
    BINDPORT=int(CONFIG.get('daemon', 'bindport'))

    LOGFILE=CONFIG.get('daemon', 'logfile')
    LOGLEVEL=LOGLEVELS[CONFIG.get('daemon', 'loglevel')]

    MODULES_DIR=CONFIG.get('daemon', 'modules_dir')


except Exception, e:
    print '[ERR] Unable to find config argument: %s' % e
    sys.exit(2)

if (OPTIONS.testconfig):
    print '[OK] Config seems to be valid'
    sys.exit(0)


def WriteLog(logstring, loglevel='info', thread='main'):
    global LOGFILE
    global OPTIONS
    global LOGLEVEL
    global LOGLEVELS

    dt = datetime.datetime.now()

    p_logstring = "%s[%s]: <%s> %s \n" % (dt.strftime("%Y-%m-%d %H:%M:%S"), loglevel.upper(), thread, logstring )

    if LOGLEVELS[loglevel.lower()] <= LOGLEVEL:

        plog = open(LOGFILE,'a')
        plog.write(p_logstring)
        plog.close()

        if OPTIONS.foreground or loglevel.upper() == 'ERROR' :
            print p_logstring,
            sys.stdout.flush()



if not os.path.exists(MODULES_DIR):
    WriteLog('no modules directory found at %s' % MODULES_DIR, 'error')
    sys.exit(1)

app = bottle.Bottle()

MODULES=[]
MOD_ROUTES = {}
MOD_ROUTES_ANY = {}

WriteLog('Looking for modules at path %s' % MODULES_DIR, 'info')

for module_dir in os.listdir(MODULES_DIR):
    module_dir_path = "%s/%s" % (MODULES_DIR, module_dir)
    if os.path.isdir(module_dir_path):
        WriteLog('Found module dir %s' % module_dir_path, 'debug')
        module_path = "%s/%s/module.py" %(MODULES_DIR, module_dir)
        if os.path.exists(module_path):
            WriteLog('Found module at path %s' % module_path, 'debug')
            imp_module = None
            HASHER.update(module_path)
            try:
                imp_module = imp.load_source(HASHER.digest(), module_path)
            except Exception as e:
                WriteLog('Error loading module at path %s : %s' % (module_path, e), 'error')
            else:
                if not hasattr(imp_module, 'name'):
                    WriteLog('Malformed module at %s: no name atribute presented' % module_path, 'error' )
                    continue

                if not hasattr(imp_module, 'routes'):
                    WriteLog('Malformed module at %s: no rotues atribute presented' % module_path, 'error' )
                    continue

                to_add = True

                for route in imp_module.routes:
                    if MOD_ROUTES_ANY.has_key(route):
                        WriteLog('Unable to accept module \'%s\' route \'%s\', because it conflicts with module \'%\'s method ANY, EXCLUDING module from initialization' % (imp_module.name, route, MOD_ROUTES_ANY[route]), 'error')
                        to_add = False
                        continue

                    if MOD_ROUTES.has_key((route, imp_module.routes[route]['method'])):
                        WriteLog('Unable to accept module \'%s\' route \'%s\' with method \'%s\', because it conflicts with module \'%s\', EXCLUDING module from initialization' %(imp_module.name, route, imp_module.routes[route]['method'], MOD_ROUTES[(route, imp_module.routes[route]['method'])]) , 'error')
                        to_add = False
                        continue

                    if imp_module.routes[route]['method'].upper() == 'ANY':
                        for m_route, m_method in MOD_ROUTES:
                            if m_route == route:
                                WriteLog('Unable to accept module \'%s\' route \'%s\' ANY method, because it conflicts with module \'%s\' method \'%s\', EXCLUDING module from initialization' % (imp_module.name, route, MOD_ROUTES[(m_route, m_method)], m_method ),'error' )
                                to_add = False
                                continue

                    if to_add:
                        MOD_ROUTES[(route, imp_module.routes[route]['method'])] = imp_module.name

                if to_add:
                    imp_module = imp.load_source(imp_module.name, module_path)

                    MODULES.append( {"module_name":imp_module.name , "module" : imp_module } )

                    WriteLog('loaded module %s at %s' % (imp_module.name, module_path) , 'info' )


INSTANCES = []


for module in MODULES:

    # kwargs = {}

    # if hasattr(module['module'], 'requirements'):
    #     if 'yadb' in module['module'].requirements:

    #         WriteLog('found dependency for module %s: %s' %(module['module'], 'yadb'), 'info')

    #         if module['module'].requirements['yadb'].has_key('db'):
    #             db=module['module'].requirements['yadb']['db']
    #         else:
    #             db='jamfsoftware'

    #         try:
    #             yadb = yadb.yadb(user=YADBUSER, host=YADBHOST, password=YADBPASSWORD, db=db)
    #         except yadb.yadbError as e:
    #             WriteLog('error creating yadb: %s for module %s, skipping module' % (e, module['module']), 'error')
    #             continue
    #         else:
    #             kwargs['yadb'] = yadb


    try:
        # instance = module['module'].apimodule(ParseReiquest, ModifyHeader, ReturnResponse, WriteLog, **kwargs)
        instance = module['module'].apimodule(bottleapp=app, WriteLog=WriteLog)

    except Exception as e:

        WriteLog('error initializing module %s: %s' % (module['module'], e), 'error')

    else:

        WriteLog('successfuly initialized module %s' % module['module'])

        # for route in instance.routes:
        #     bottle.route(route['path'], method=route["method"])(instance.ProccessRoute)
        #     WriteLog('module %s bound route %s' % (instance.name, route['path']))

        INSTANCES.append(instance)


WriteLog('Initialized api with modules %s' % INSTANCES.__str__())


# def signal_handle(signum, frame):
    # print 'signal %s and frame %s' % (signum, frame)


# signal.signal(signal.SIGUSR1, signal_handle)

class BottleServer(Thread):
    """docstring for BottleServer"""

    def __init__(self, bottleapp):
        super(BottleServer, self).__init__()
        self.bottleapp=bottleapp

    def run(self):
        app.run(host=BINDIP, port=BINDPORT, debug=False, server='paste')
        



        
# while True:
bTh = BottleServer(app)
bTh.daemon = False
bTh.run()


