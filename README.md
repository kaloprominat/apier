apier
=====

Requirements:

* python-bottle

```
Usage: apier.py [options]

Options:
  -h, --help            show this help message and exit
  -c CONFIGFILE, --config=CONFIGFILE
                        configuration file path
  -t, --test-config     do not run, just test specified config
  -f, --foreground      run in silent mode, only errors will be reported
  -l FORCEDLOGLEVEL, --loglevel=FORCEDLOGLEVEL
                        specifies loglevel, overrides loglevel from config
                        file. available levels: warn,info,silent,debug,error
```

To start apier in debug mode and foreground, perform

```python apier.py -c ./daemon.conf -f -l debug```

To start developing apier module:

1. git clone https://github.com/kaloprominat/apier.git ./apier
2. cd apier
3. make install-apiermodule
4. create your own module from example
5. python module.py
