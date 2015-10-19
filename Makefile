all: sdist
    
sdist:
	python setup.py sdist

install-apiermodule:
	@sudo python setup.py install

clean:
	rm -rf ./venv

virtualenv:
	virtualenv --version || ( echo "No virtualenv installed!"; exit 127 )

venv: virtualenv
	if [ ! -d ./venv ]; then \
	virtualenv --no-site-packages ./venv ;\
	source venv/bin/activate ;\
	pip install bottle==0.12.7 ;\
	pip install cherrypy==3.2.2 ;\
	fi

run: venv
	source venv/bin/activate ;\
	python apier.py -c ./daemon.conf -f -l debug ;\
	deactivate