#!/usr/bin/python
# -*- coding: utf-8 -*-


__version__ = '0.2.1'

#   Some general imports

import sys
import thread   # for threading purposes  
import imp      # for loading modules dynamically
import os
import json
import ConfigParser     # for parsing config
import datetime
import signal       # for future signal support
import traceback    # for detalaized errors in runtime
import socket       # for bind address resolution

#   For threading and options parsing

from threading import Thread
from optparse import OptionParser

# main web server framework

import bottle

#   This part for http access logging

from requestlogger import WSGILogger, ApacheFormatter
from logging.handlers import TimedRotatingFileHandler

import cherrypy

#   This hack is for disabling reverse DNS lookups

__import__('BaseHTTPServer').BaseHTTPRequestHandler.address_string = lambda x:x.client_address[0]


#   This is for disabling warnings

import warnings
warnings.filterwarnings("ignore")

#   Class for future colorizing

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

#   Logger class for http server

class Logger(object):
    def __init__(self, filename="./http.log", foreground=False):
        self.foreground = foreground
        self.terminal = sys.stdout
        self.log = open(filename, "a")

    def write(self, message):
        if self.foreground:
            self.terminal.write(message)
        self.log.write(message)
        self.terminal.flush()
        self.log.flush()


#   Global loglevels

LOGLEVELS = {
    "silent"    : 0,
    "error"     : 1,
    "warn"      : 2,
    "info"      : 3,
    "debug"     : 4
}

LOGLEVEL = LOGLEVELS['debug']

PARSER = OptionParser()

PARSER.add_option('-c', '--config', dest='configfile',
                        help='configuration file path',
                        default='/etc/apier/daemon.conf'
                        )
PARSER.add_option('-t', '--test-config', dest='testconfig',
                        help='do not run, just test specified config',
                        action='store_true'
                        )

PARSER.add_option('-f', '--foreground', dest='foreground',
                        help='run in silent mode, only errors will be reported',
                        action='store_true'
                        )

PARSER.add_option('-l', '--loglevel', dest='forcedloglevel',
                        help='specifies loglevel, overrides loglevel from config file. available levels: %s' % ','.join(LOGLEVELS.keys()),
                        default=None
                        )

OPTIONS, ARGS = PARSER.parse_args()

CONFIGFILE = OPTIONS.configfile

CONFIG = ConfigParser.RawConfigParser(allow_no_value=True)


#   Trying read config file

try:
    CONFIG.read(CONFIGFILE)
except Exception, e:
    print '[ERR] Error loading config file: %s' % e
    print traceback.format_exc(e)
    sys.exit(1)

try:

    # BINDIP=CONFIG.get('daemon', 'bindip')

    if 'bindip' in CONFIG.options('daemon'):
        BINDIP = CONFIG.get('daemon', 'bindip')
    else:
        BINDIP = None

    BINDPORT=int(CONFIG.get('daemon', 'bindport'))

    HTTPACCESSLOGFILE=CONFIG.get('daemon', 'httpaccesslogfile')
    LOGFILE=CONFIG.get('daemon', 'logfile')

    LOGLEVEL=LOGLEVELS[CONFIG.get('daemon', 'loglevel')]

    MODULES_DIR=CONFIG.get('daemon', 'modules_dir')

    if 'conf_dir' in CONFIG.options('daemon'):

        CONF_DIR=CONFIG.get('daemon', 'conf_dir')
    else:
        CONF_DIR=None

    if 'bindipv6' in CONFIG.options('daemon'):
        BINDIPV6 = CONFIG.get('daemon', 'bindipv6')
    else:
        BINDIPV6 = None

except Exception, e:
    print '[ERR] Unable to find config argument: %s' % e
    print traceback.format_exc(e)
    sys.exit(2)

if (OPTIONS.testconfig):
    print '[OK] Config seems to be valid'
    sys.exit(0)


sys.stderr = Logger(LOGFILE, OPTIONS.foreground)

if OPTIONS.forcedloglevel != None:
    LOGLEVEL=LOGLEVELS[OPTIONS.forcedloglevel]


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
            # sys.stderr.flush()

    if thread != 'main':
        plog = open( '%s/%s.log' % ( os.path.dirname(LOGFILE), thread ), 'a')
        plog.write(p_logstring)
        plog.close()


if not os.path.exists(MODULES_DIR):
    WriteLog('no modules directory found at %s' % MODULES_DIR, 'error')
    sys.exit(1)

WriteLog('Apier version: %s' % __version__, 'info')
WriteLog('Python version: %s' % sys.version, 'info')
WriteLog('Bottle version: %s' % bottle.__version__)
WriteLog('cherrypy version: %s' % cherrypy.__version__)

#   This part is for determining ipv6 adresses to bind

BINDIPV6S = []

if BINDIPV6 == '::' :

    BINDIPV6S.append('::1')

    try:
        ipv6details = socket.getaddrinfo(socket.getfqdn(), None, socket.AF_INET6)
    except Exception, e:
        WriteLog('No external ipv6 address found, using local socket at ::1', 'warn')
    else:
        BINDIPV6S.append(ipv6details[1][4][0])

elif BINDIPV6 == 'ext' :

    try:
        ipv6details = socket.getaddrinfo(socket.getfqdn(), None, socket.AF_INET6)
    except Exception, e:
        WriteLog('No external ipv6 address found, but _ext_ address specified, aborting', 'error')
        raise e
    else:
        BINDIPV6S.append(ipv6details[1][4][0])

else:
    BINDIPV6S.append(BINDIPV6)

CONFIGS = {}

#   Listing conf.d directory

if CONF_DIR != None and os.path.isdir(CONF_DIR):

    WriteLog('Found conf.d directory at path %s' % CONF_DIR, 'info')

    for conf_file in os.listdir(CONF_DIR):
        conf_file_path = "%s/%s" % (CONF_DIR, conf_file)
        if not os.path.isfile(conf_file_path):
            WriteLog('Found item at %s is not a file' % conf_file_path, 'warn')
        else:

            if '.conf' in conf_file_path:

                CONFIG_D = ConfigParser.RawConfigParser(allow_no_value=True)
                try:
                    CONFIG_D.read(conf_file_path)
                except Exception as e:
                    WriteLog('Error "%s" parsing config at "%s"' % ( e.__str__().replace("\n", " ") , conf_file_path ), 'error' )
                else:
                    CONFIGS[conf_file] = {}

                    for section in CONFIG_D.sections():
                        CONFIGS[conf_file][section] = {}

                        for item in CONFIG_D.items(section):
                            CONFIGS[conf_file][section][item[0]] = item[1]

                    WriteLog('Found and processed config %s with sections %s' % ( conf_file , CONFIG_D.sections().__str__() ), 'info' )

            if '.json' in conf_file_path:

                try:
                    with open(conf_file_path) as data_file:    
                        CONFIG_D = json.load(data_file)
                except Exception as e:
                    WriteLog('Error "%s" parsing config at "%s"' % ( e.__str__().replace("\n", " ") , conf_file_path ), 'error' )
                else:
                    CONFIGS[conf_file] = CONFIG_D

                    WriteLog('Found and processed json config %s' %  conf_file, 'info' )

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
            try:
                imp_module = imp.load_source(module_path, module_path)
            except Exception as e:
                WriteLog('Error loading module at path %s : %s' % (module_path, e), 'error')
                WriteLog('%s' % traceback.format_exc(e), 'error' )
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

    try:

        instance = module['module'].apimodule(bottleapp=app, WriteLog=WriteLog, configs = CONFIGS)

    except Exception as e:

        WriteLog('error initializing module %s: %s' % (module['module'], e), 'error')
        WriteLog('%s' % traceback.format_exc(e), 'error' )

    else:

        WriteLog('successfuly initialized module %s' % module['module'])

        INSTANCES.append(instance)


WriteLog('Initialized api with modules %s' % INSTANCES.__str__())


# def signal_handle(signum, frame):
    # print 'signal %s and frame %s' % (signum, frame)


# signal.signal(signal.SIGUSR1, signal_handle)

class BottleServer(Thread):
    """docstring for BottleServer"""

    def __init__(self, bottleapp, CBINDIP):
        
        self.bottleapp=bottleapp
        self.BINDIP=CBINDIP

        super(BottleServer, self).__init__()

    def run(self):
        WriteLog('Apier %s started on [%s]:%s' % (__version__, self.BINDIP, BINDPORT) )
        bottle.run(app=self.bottleapp, host=self.BINDIP, port=BINDPORT, server='cherrypy', quiet=True)


#   Defining loggin things

handlers = [ TimedRotatingFileHandler(HTTPACCESSLOGFILE, 'd', 7) , ]
loggedapp = WSGILogger(app, handlers, ApacheFormatter())

if BINDIP != None and BINDIPV6 != None:

    if BINDIPV6 != None:

        for ipv6 in BINDIPV6S:
            bTh6 = BottleServer(loggedapp, ipv6)
            bTh6.daemon = True
            bTh6.start()

    bTh = BottleServer(loggedapp, BINDIP)
    bTh.daemon = True

    bTh.run()


else:

    if BINDIPV6 != None:
        bTh6 = BottleServer(loggedapp, BINDIPV6)
        bTh6.daemon = True
        bTh6.run()
    else:
        bTh6 = BottleServer(loggedapp, BINDIP)
        bTh6.daemon = True
        bTh6.run()


