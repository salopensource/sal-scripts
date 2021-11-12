#!/bin/zsh
# Build script for Python 3 framework for Sal scripts
TOOLSDIR=$(dirname "$0")
PYTHON_VERSION=3.9.7

# build the framework
/tmp/relocatable-python-git/make_relocatable_python_framework.py \
    --python-version "${PYTHON_VERSION}" \
    --pip-requirements requirements.txt \
    --destination "${TOOLSDIR}" \
    --os-version "11" \
    --upgrade-pip

# Stolen with love from https://github.com/macadmins/python/blob/main/build_python_framework_pkgs.zsh
TOTAL_DYLIB=$(/usr/bin/find "${TOOLSDIR}/Python.framework/Versions/Current/lib" -name "*.dylib" | /usr/bin/wc -l | /usr/bin/xargs)
UNIVERSAL_DYLIB=$(/usr/bin/find "${TOOLSDIR}/Python.framework/Versions/Current/lib" -name "*.dylib" | /usr/bin/xargs file | /usr/bin/grep "2 architectures" | /usr/bin/wc -l | /usr/bin/xargs)
if [ "${TOTAL_DYLIB}" != "${UNIVERSAL_DYLIB}" ] ; then
  echo "Dynamic Libraries do not match, resulting in a non-universal Python framework."
  echo "Total Dynamic Libraries found: ${TOTAL_DYLIB}"
  echo "Universal Dynamic Libraries found: ${UNIVERSAL_DYLIB}"
  exit 1
fi

echo "Dynamic Libraries are confirmed as universal"

TOTAL_SO=$(/usr/bin/find "${TOOLSDIR}/Python.framework/Versions/Current/lib" -name "*.so" | /usr/bin/wc -l | /usr/bin/xargs)
UNIVERSAL_SO=$(/usr/bin/find "${TOOLSDIR}/Python.framework/Versions/Current/lib" -name "*.so" | /usr/bin/xargs file | /usr/bin/grep "2 architectures" | /usr/bin/wc -l | /usr/bin/xargs)
if [ "${TOTAL_SO}" != "${UNIVERSAL_SO}" ] ; then
  echo "Shared objects do not match, resulting in a non-universal Python framework."
  echo "Total shared objects found: ${TOTAL_SO}"
  echo "Universal shared objects found: ${UNIVERSAL_SO}"
  UNIVERSAL_SO_ARRAY=("${(@f)$(/usr/bin/find "${TOOLSDIR}/Python.framework/Versions/Current/lib" -name "*.so" | /usr/bin/xargs file | /usr/bin/grep "2 architectures"  | awk '{print $1;}' | sed 's/:*$//g')}")
  TOTAL_SO_ARRAY=("${(@f)$(/usr/bin/find "${TOOLSDIR}/Python.framework/Versions/Current/lib" -name "*.so" )}")
  echo ${TOTAL_SO_ARRAY[@]} ${UNIVERSAL_SO_ARRAY[@]} | tr ' ' '\n' | sort | uniq -u
  exit 1
fi