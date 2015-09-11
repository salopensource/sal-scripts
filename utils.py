#!/usr/bin/python
import tempfile
from Foundation import *
import os
import sys
import subprocess

BUNDLE_ID = 'com.github.salopensource.sal'
class GurlError(Exception):
    pass

class HTTPError(Exception):
    pass

def set_pref(pref_name, pref_value):
    """Sets a preference, writing it to
        /Library/Preferences/com.salopensource.sal.plist.
        This should normally be used only for 'bookkeeping' values;
        values that control the behavior of munki may be overridden
        elsewhere (by MCX, for example)"""
    try:
        CFPreferencesSetValue(
                              pref_name, pref_value, BUNDLE_ID,
                              kCFPreferencesAnyUser, kCFPreferencesCurrentHost)
        CFPreferencesAppSynchronize(BUNDLE_ID)
    except Exception:
        pass

def pref(pref_name):
    """Return a preference. Since this uses CFPreferencesCopyAppValue,
    Preferences can be defined several places. Precedence is:
        - MCX
        - /var/root/Library/Preferences/com.salopensource.sal.plist
        - /Library/Preferences/com.salopensource.sal.plist
        - default_prefs defined here.
    """
    default_prefs = {
        'ServerURL': 'http://sal',
        'osquery_launchd': 'com.facebook.osqueryd.plist'
    }
    pref_value = CFPreferencesCopyAppValue(pref_name, BUNDLE_ID)
    if pref_value == None:
        pref_value = default_prefs.get(pref_name)
        # we're using a default value. We'll write it out to
        # /Library/Preferences/<BUNDLE_ID>.plist for admin
        # discoverability
        set_pref(pref_name, pref_value)
    if isinstance(pref_value, NSDate):
        # convert NSDate/CFDates to strings
        pref_value = str(pref_value)
    return pref_value

def curl(url, data=None):
    if data:
        cmd = ['/usr/bin/curl','--connect-timeout', '10', '--data', data, url]
    else:
        cmd = ['/usr/bin/curl', '--connect-timeout', '10', url]
    task = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = task.communicate()
    if task.returncode == 0:
        stderr = None
    return stdout, stderr