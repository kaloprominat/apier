#!/usr/bin/env python
# -*- coding: utf-8 -*-

# common dependencies
import signal
import logging
import sys
import os
import socket
import imp
import time

# web framework
import bottle

# wsgi server
import cherrypy
from cherrypy.wsgiserver import CherryPyWSGIServer

# threading
from threading import Thread

# configs & options
import ConfigParser
from optparse import OptionParser

#   This is for disabling warnings
import warnings
warnings.filterwarnings("ignore")


__version__ = '1.0.1'


logging.basicConfig(format='%(asctime)s [%(name)s]\t%(levelname)s\t%(message)s',
                    level=logging.DEBUG)
log = logging.getLogger(__name__ if __name__ != '__main__' else 'apier')


LOGLEVELS = {
    "silent"    : logging.NOTSET,
    "error"     : logging.ERROR,
    "warn"      : logging.WARN,
    "info"      : logging.INFO,
    "debug"     : logging.DEBUG
}


# Options parsing

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

# Configuration file

CONFIG = ConfigParser.RawConfigParser(allow_no_value=True)

log.debug('Config file: %s', OPTIONS.configfile)

if not os.path.exists(OPTIONS.configfile):
    log.error('Config file does not exists: %s', OPTIONS.configfile)
    sys.exit(1)

try:
    CONFIG.read(OPTIONS.configfile)
except Exception, e:
    log.error('Error loading config file: %s', e, exc_info=1)
    sys.exit(1)

# Configuration file options

try:
    if 'bindip' in CONFIG.options('daemon'):
        BINDIP = CONFIG.get('daemon', 'bindip')
    else:
        BINDIP = None

    BINDPORT = int(CONFIG.get('daemon', 'bindport'))

    HTTPACCESSLOGFILE = CONFIG.get('daemon', 'httpaccesslogfile')
    LOGFILE = CONFIG.get('daemon', 'logfile')

    LOGLEVEL = LOGLEVELS[CONFIG.get('daemon', 'loglevel')]

    MODULES_DIR = CONFIG.get('daemon', 'modules_dir')

    if 'reload_modules' in CONFIG.options('daemon'):
        RELOAD_MODULES = CONFIG.get('daemon', 'reload_modules')
    else:
        RELOAD_MODULES = 0

    if 'conf_dir' in CONFIG.options('daemon'):

        CONF_DIR = CONFIG.get('daemon', 'conf_dir')
    else:
        CONF_DIR = None

    if 'bindipv6' in CONFIG.options('daemon'):
        BINDIPV6 = CONFIG.get('daemon', 'bindipv6')
    else:
        BINDIPV6 = None

except Exception, e:
    log.error('Unable to find config argument: %s', e, exc_info=1)
    sys.exit(1)

if (OPTIONS.testconfig):
    log.info('[OK] Config seems to be valid')
    sys.exit(0)

if OPTIONS.forcedloglevel is not None:
    LOGLEVEL = LOGLEVELS[OPTIONS.forcedloglevel]

log.setLevel(LOGLEVEL)

# modules dir

if not os.path.exists(MODULES_DIR):
    log.error('No modules directory found at %s', MODULES_DIR)
    sys.exit(1)


# Start here

log.info('Apier version: %s', __version__)
log.info('Python version: %s', sys.version.replace("\n", " "))
log.info('Bottle version: %s', bottle.__version__)
log.info('Cherrypy version: %s', cherrypy.__version__)

log.info('Starting apier...')


# Determining bind interfaces

def bind_addresses():

    global BINDADDRESSES

    BINDADDRESSES = [BINDIP]

    if BINDIPV6 == '::' :
        BINDADDRESSES.append('::1')

        try:
            ipv6details = socket.getaddrinfo(socket.getfqdn(), None, socket.AF_INET6)
        except Exception, e:
            log.warn('No external ipv6 address found, using local socket at ::1')
        else:
            BINDADDRESSES.append(ipv6details[1][4][0])

    elif BINDIPV6 == 'ext' :

        try:
            ipv6details = socket.getaddrinfo(socket.getfqdn(), None, socket.AF_INET6)
        except Exception, e:
            log.error('No external ipv6 address found, but _ext_ address specified, aborting')
            raise e
        else:
            BINDADDRESSES.append(ipv6details[1][4][0])

    else:
        if BINDIPV6 is not None:
            BINDADDRESSES.append(BINDIPV6)

    log.info('Bind sockets: %s:%s', BINDADDRESSES, BINDPORT)


def reloadModules():

    global app
    global APIER_MODULES

    log.debug('Looking for modules at path %s', MODULES_DIR)

    for module_dir in os.listdir(MODULES_DIR):
        module_dir_path = "%s/%s" % (MODULES_DIR, module_dir)
        if os.path.isdir(module_dir_path):
            # log.debug('Found module dir %s', module_dir_path)
            module_path = "%s/%s/module.py" % (MODULES_DIR, module_dir)
            if os.path.exists(module_path):
                log.debug('Found module at path %s', module_path)
                imp_module = None
                try:
                    imp_module = imp.load_source(module_path, module_path)
                except Exception as e:
                    log.error('Error loading module at path %s : %s', module_path, e, exc_info=1)
                else:
                    if not hasattr(imp_module, 'name'):
                        log.error('Malformed module at %s: no name atribute presented', module_path)
                        continue

                    if not hasattr(imp_module, 'routes'):
                        log.error('Malformed module at %s: no rotues atribute presented', module_path)
                        continue

                    to_add = True

                    # for route in imp_module.routes:
                    #     if MOD_ROUTES_ANY.has_key(route):
                    #         WriteLog('Unable to accept module \'%s\' route \'%s\', because it conflicts with module \'%\'s method ANY, EXCLUDING module from initialization' % (imp_module.name, route, MOD_ROUTES_ANY[route]), 'error')
                    #         to_add = False
                    #         continue

                    #     if MOD_ROUTES.has_key((route, imp_module.routes[route]['method'])):
                    #         WriteLog('Unable to accept module \'%s\' route \'%s\' with method \'%s\', because it conflicts with module \'%s\', EXCLUDING module from initialization' %(imp_module.name, route, imp_module.routes[route]['method'], MOD_ROUTES[(route, imp_module.routes[route]['method'])]) , 'error')
                    #         to_add = False
                    #         continue

                    #     if imp_module.routes[route]['method'].upper() == 'ANY':
                    #         for m_route, m_method in MOD_ROUTES:
                    #             if m_route == route:
                    #                 WriteLog('Unable to accept module \'%s\' route \'%s\' ANY method, because it conflicts with module \'%s\' method \'%s\', EXCLUDING module from initialization' % (imp_module.name, route, MOD_ROUTES[(m_route, m_method)], m_method ),'error' )
                    #                 to_add = False
                    #                 continue

                    #     if to_add:
                    #         MOD_ROUTES[(route, imp_module.routes[route]['method'])] = imp_module.name

                    if to_add:
                        imp_module = imp.load_source(imp_module.name, module_path)

                        if imp_module.name not in APIER_MODULES:

                            APIER_MODULES[imp_module.name] = {
                                'module_name'   : imp_module.name,
                                'module'        : imp_module,
                                'path'          : module_path.replace('.pyc','.py'),
                                'instance'      : None,
                                'mtime'         : long(os.path.getmtime(module_path.replace('.pyc','.py')))
                            }

                        else:

                            APIER_MODULES[imp_module.name]['module'] = imp_module
                            APIER_MODULES[imp_module.name]['instance'] = None
                            APIER_MODULES[imp_module.name]['mtime'] = long(os.path.getmtime(module_path.replace('.pyc','.py')))

                        log.info('Loaded module %s at %s', imp_module.name, module_path)


def initModules():

    global app
    global APIER_MODULES

    for module_name in APIER_MODULES:

        module = APIER_MODULES[module_name]

        try:

            instance = module['module'].apimodule(bottleapp=app, loglevel=LOGLEVEL)

        except Exception as e:

            log.error('Error init %s: %s', module['module'], e, exc_info=1)
            APIER_MODULES[module_name]['instance'] = None

        else:

            log.info('Init %s', module['module'])

            APIER_MODULES[module_name]['instance'] = instance

    log.info('Init app with %s', [ APIER_MODULES[x]['instance'] for x in APIER_MODULES ] )


def createApp():
    global app
    app = bottle.Bottle()
    log.debug('Created bottle app %s', app)


def createServers():
    global app
    global BINDADDRESSES
    svs = []
    for bip in BINDADDRESSES:
        s = CherryPyWSGIServer((bip, BINDPORT), app)
        svs.append(s)
    return svs


def run_server(s):
    try:
        log.debug('Starting %s', s)
        s.start()
    except Exception, e:
        log.error('Failed to start server %s:%s', s, e, exc_info=1)


def start_servers():

    global SERVERS

    for s in SERVERS:
        st = Thread(target=run_server, args=(s,))
        st.daemon = True
        st.start()


def stop_servers():

    global SERVERS

    for s in SERVERS:
        sr = s.ready
        s.stop()
        if sr:
            log.debug('%s stoped', s)


def restart_servers():
    stop_servers()
    start_servers()


def startServers(svs):
    global SERVERS
    stop_servers()
    SERVERS = svs
    start_servers()


# Global variables

SERVERS = []
APIER_MODULES = {}
BINDADDRESSES = []

app = None


# refresing thread

class ModulesRefreshThread(Thread):

    def __init__(self):

        super(ModulesRefreshThread, self).__init__()

    def run(self):

        global APIER_MODULES

        log.info('Module reloading thread started')

        while True:
            for module_name in APIER_MODULES:
                module = APIER_MODULES[module_name]
                mtime = long(os.path.getmtime(module['path']))

                if module['mtime'] != mtime:
                    log.info('Reloading modules %s' % module['module'])

                    reloadModules()
                    createApp()
                    initModules()
                    startServers(createServers())

            time.sleep(1)


def sigint_handle(signum, frame):

    log.warn('SIGINT received, stopping...')
    stop_servers()


signal.signal(signal.SIGINT, sigint_handle)
signal.signal(signal.SIGABRT, sigint_handle)
signal.signal(signal.SIGTERM, sigint_handle)
signal.signal(signal.SIGUSR1, sigint_handle)

if __name__ == '__main__':

    # main loop here

    __name__ = 'apier'

    bind_addresses()
    reloadModules()
    createApp()
    initModules()

    startServers(createServers())

    if int(RELOAD_MODULES) == 1:

        mrt = ModulesRefreshThread()
        mrt.daemon = True
        mrt.start()

    signal.pause()
