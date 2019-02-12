USE_PKGBUILD=1
include /usr/local/share/luggage/luggage.make
PACKAGE_VERSION:=$(shell sed -n -e '/^VERSION/p' payload/usr/local/sal/utils.py | cut -d "'" -f 2)
TITLE=sal_scripts
PACKAGE_NAME=sal_scripts
REVERSE_DOMAIN=com.github.salopensource
PAYLOAD=\
	pack-sal-scripts \
	pack-report-broken-client \
	pack-Library-LaunchDaemons-com.salopensource.sal.runner.plist \
	pack-Library-LaunchDaemons-com.salopensource.sal.random.runner.plist \
	pack-script-postinstall

clean-build:
	rm -rf report_broken_client/build

pack-report-broken-client: pack-sal-scripts clean-build
	xcodebuild -project report_broken_client/report_broken_client.xcodeproj -configuration Release
	@sudo ${CP} report_broken_client/build/Release/report_broken_client ${WORK_D}/usr/local/munki/report_broken_client

pack-sal-scripts: l_usr_local
	@sudo ${CP} -R payload/ ${WORK_D}
	@sudo chown -R root:wheel ${WORK_D}
	@sudo chmod -R 755 ${WORK_D}

install: pkg
	@sudo installer -pkg sal_scripts.pkg -target /