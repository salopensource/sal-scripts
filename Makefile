USE_PKGBUILD=1
include /usr/local/share/luggage/luggage.make
PACKAGE_VERSION:=$(shell sed -n -e '/^VERSION/p' payload/usr/local/sal/bin/sal-submit | cut -d "'" -f 2)
TITLE=sal_scripts
PACKAGE_NAME=sal_scripts
REVERSE_DOMAIN=com.github.salopensource
PAYLOAD=\
	pack-sal-scripts \
	pack-Library-LaunchDaemons-com.salopensource.sal.runner.plist \
	pack-script-postinstall

# GOPATH="$(shell pwd)/vendor:$(shell pwd)"
# GOBIN="$(shell pwd)/bin"
# GOFILES=$(wildcard *.go)
# GONAME=$(shell basename "$(PWD)")

# pack-broken-client: pack-sal-scripts
# 	@GOPATH=$(GOPATH) GOBIN=$(GOBIN) go get .
# 	@GOPATH=$(GOPATH) GOBIN=$(GOBIN) go build report_broken_client.go
#	@sudo ${CP} report_broken_client ${WORK_D}/usr/local/munki/report_broken_client
#	@sudo chown root:wheel ${WORK_D}/usr/local/munki/report_broken_client	
# 	@sudo chmod 755 ${WORK_D}/usr/local/munki/report_broken_client

# pack-yaml: l_usr_local
# 	@sudo find . -name "*.pyc" -exec rm -rf {} \;
# 	@sudo mkdir -p ${WORK_D}/usr/local/sal/yaml
# 	@sudo mkdir -p ${WORK_D}/usr/local/sal/bin
# 	@sudo ${CP} -R ../yaml ${WORK_D}/usr/local/sal
# 	@sudo chown -R root:wheel ${WORK_D}/usr/local/sal
# 	@sudo chmod -R 755 ${WORK_D}/usr/local/sal
# 	@sudo ${INSTALL} -m 755 -g wheel -o root ../"utils.py" ${WORK_D}/usr/local/sal
# 	@sudo ${INSTALL} -m 755 -g wheel -o root ../"sal-postflight" ${WORK_D}/usr/local/sal/bin

# l_munki: l_usr_local
# 	@sudo mkdir -p ${WORK_D}/usr/local/munki/postflight.d
# 	@sudo chown root:wheel ${WORK_D}/usr/local/munki/postflight.d
# 	@sudo mkdir -p ${WORK_D}/usr/local/munki/preflight.d
# 	@sudo chown root:wheel ${WORK_D}/usr/local/munki/preflight.d

# pack-sal-submit: l_munki broken_client
# 	@sudo ${INSTALL} -m 755 -g wheel -o root ../"postflight" ${WORK_D}/usr/local/munki
# 	@sudo ${INSTALL} -m 755 -g wheel -o root ../"preflight" ${WORK_D}/usr/local/munki
# 	@sudo ${INSTALL} -m 755 -g wheel -o root ../"postflight.d/sal-postflight" ${WORK_D}/usr/local/munki/postflight.d
# 	@sudo ${INSTALL} -m 755 -g wheel -o root ../"preflight.d/sal-preflight" ${WORK_D}/usr/local/munki/preflight.d
# 	@sudo ${INSTALL} -m 755 -g wheel -o root ../"report_broken_client" ${WORK_D}/usr/local/munki


pack-sal-scripts: l_usr_local
	@sudo ${CP} -R payload/ ${WORK_D}
	@sudo chown -R root:wheel ${WORK_D}
	@sudo chmod -R 755 ${WORK_D}