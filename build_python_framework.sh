#!/bin/zsh

# Build script for Python 3 framework for Sal scripts
TOOLSDIR=$(dirname "$0")
PYTHON_VERSION=3.9.5
PYTHON_SHORT=3.9
MACOS_VERSION=11 # use 10.9 for non-universal
DevApp=$1

# build the framework
/tmp/relocatable-python-git/make_relocatable_python_framework.py \
    --python-version "${PYTHON_VERSION}" \
    --pip-requirements requirements.txt \
    --os-version "${MACOS_VERSION}" \
    --destination "${TOOLSDIR}" \
    --upgrade-pip

# sign all the bits of python with our Apple Developer ID Installer: cert.
find ${TOOLSDIR}/Python.framework -name '*.pyc' -delete
find ${TOOLSDIR}/Python.framework/Versions/${PYTHON_SHORT}/lib/ -type f -perm -u=x -exec codesign --force --deep --verbose -s "$DevApp" {} \;
find ${TOOLSDIR}/Python.framework/Versions/${PYTHON_SHORT}/bin/ -type f -perm -u=x -exec codesign --force --deep --verbose -s "$DevApp" {} \;
find ${TOOLSDIR}/Python.framework/Versions/${PYTHON_SHORT}/lib/ -type f -name "*dylib" -exec codesign --force --deep --verbose -s "$DevApp" {} \;

/usr/libexec/PlistBuddy -c "Add :com.apple.security.cs.allow-unsigned-executable-memory bool true" ${TOOLSDIR}/entitlements.plist

codesign --force --options runtime --entitlements $TOOLSDIR/entitlements.plist --deep --verbose -s "$DevApp" $TOOLSDIR/Python.framework/Versions/${PYTHON_SHORT}/Resources/Python.app/
codesign --force --deep --options runtime --entitlements $TOOLSDIR/entitlements.plist --deep --verbose -s "$DevApp" $TOOLSDIR/Python.framework/Versions/${PYTHON_SHORT}/bin/*
codesign --force --deep --options runtime --entitlements $TOOLSDIR/entitlements.plist --deep --verbose -s "$DevApp" $TOOLSDIR/Python.framework/Versions/${PYTHON_SHORT}/lib/*
codesign --force --deep --options runtime --entitlements $TOOLSDIR/entitlements.plist --deep --verbose -s "$DevApp" $TOOLSDIR/Python.framework/Versions/${PYTHON_SHORT}/python
codesign --force --deep --verbose -s "$DevApp" $TOOLSDIR/Python.framework
codesign --force --deep --options runtime --entitlements $TOOLSDIR/entitlements.plist --deep --verbose -s "$DevApp" $TOOLSDIR/Python.framework/python