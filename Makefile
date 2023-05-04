USE_PKGBUILD=1
include luggage/luggage.make
include config.mk
PACKAGE_VERSION:=$(shell sed -n -e '/^__version__/p' sal_python_pkg/sal/version.py | cut -d "\"" -f 2)
PB_EXTRA_ARGS+= --sign "${DEV_INSTALL_CERT}"
.PHONY: remove-xattrs sign clean-build
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
	pack-python \
	remove-xattrs \
	sign

clean-build:
	killall Dropbox || true
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
	@sudo ${RM} -f /tmp/sal_scripts.pkg
	@sudo ${CP} sal_scripts.pkg /tmp/sal_scripts.pkg
	@sudo installer -pkg /tmp/sal_scripts.pkg -target /

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

sign: remove-xattrs
	@sudo ./sign_python_framework.py -v -S "${DEV_APP_CERT}" -L ${WORK_D}/usr/local/sal/Python.framework

remove-xattrs:
	@sudo xattr -rd com.dropbox.attributes ${WORK_D}
	@sudo xattr -rd com.dropbox.internal ${WORK_D}
	@sudo xattr -rd com.apple.ResourceFork ${WORK_D}
	@sudo xattr -rd com.apple.FinderInfo ${WORK_D}
	@sudo xattr -rd com.apple.metadata:_kMDItemUserTags ${WORK_D}
	@sudo xattr -rd com.apple.metadata:kMDItemFinderComment ${WORK_D}
	@sudo xattr -rd com.apple.metadata:kMDItemOMUserTagTime ${WORK_D}
	@sudo xattr -rd com.apple.metadata:kMDItemOMUserTags ${WORK_D}
	@sudo xattr -rd com.apple.metadata:kMDItemStarRating ${WORK_D}
	@sudo xattr -rd com.dropbox.ignored ${WORK_D}