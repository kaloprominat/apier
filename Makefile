all: sdist
    
sdist:
	python setup.py sdist

install-apiermodule:
	@sudo python setup.py install