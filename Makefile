USE_PKGBUILD=1
include /usr/local/share/luggage/luggage.make
PACKAGE_VERSION:=$(shell sed -n -e '/^__version__/p' sal_python_pkg/sal/version.py | cut -d "'" -f 2)
TITLE=sal_scripts
PACKAGE_NAME=sal_scripts
REVERSE_DOMAIN=com.github.salopensource
PYTHONTOOLDIR=/tmp/relocatable-python-git
PAYLOAD=\
	pack-sal-scripts \
	pack-report-broken-client \
	pack-Library-LaunchDaemons-com.salopensource.sal.runner.plist \
	pack-Library-LaunchDaemons-com.salopensource.sal.random.runner.plist \
	pack-script-postinstall \
	pack-python

clean-build:
	@sudo rm -rf report_broken_client/build

pack-report-broken-client: pack-sal-scripts clean-build
	xcodebuild -project report_broken_client/report_broken_client.xcodeproj -configuration Release
	@sudo ${CP} report_broken_client/build/Release/report_broken_client ${WORK_D}/usr/local/munki/report_broken_client

pack-sal-scripts: l_usr_local
	@sudo find . -name '*.pyc' -delete
	@sudo ${CP} -R payload/ ${WORK_D}
	@sudo chown -R root:wheel ${WORK_D}
	@sudo chmod -R 755 ${WORK_D}

install: pkg
	@sudo installer -pkg sal_scripts.pkg -target /

pack-python: clean-python build-python
	@sudo ${CP} -R Python.framework ${WORK_D}/usr/local/sal/
	@sudo chown -R root:wheel ${WORK_D}/usr/local/sal/Python.framework
	@sudo chmod -R 755 ${WORK_D}/usr/local/sal/Python.framework

clean-python:
	@sudo ${RM} -rf Python.framework
	@sudo ${RM} -rf ${WORK_D}/usr/local/sal/Python.framework

build-python:
	# Why not just run the make_relocatable_python.py here?
	# It can't find the temp folder that the python pkg is expanded into
	# if issued directly from Make, so we're currently shelling out until
	# we grok the GNU better.
	@rm -rf "${PYTHONTOOLDIR}"
	@git clone https://github.com/gregneagle/relocatable-python.git "${PYTHONTOOLDIR}"
	@./build_python_framework.sh
	@find ./Python.framework -name '*.pyc' -delete