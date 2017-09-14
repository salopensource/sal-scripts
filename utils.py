#!/usr/bin/python


import hashlib
import os
import subprocess
import sys
import tempfile


from Foundation import *


BUNDLE_ID = 'com.github.salopensource.sal'


class GurlError(Exception):
    pass


class HTTPError(Exception):
    pass


def set_pref(pref_name, pref_value):
    """Sets a Sal preference.

    The preference file on disk is located at
    /Library/Preferences/com.salopensource.sal.plist.  This should
    normally be used only for 'bookkeeping' values; values that control
    the behavior of munki may be overridden elsewhere (by MCX, for
    example)"""
    try:
        CFPreferencesSetValue(
            pref_name, pref_value, BUNDLE_ID, kCFPreferencesAnyUser,
            kCFPreferencesCurrentHost)
        CFPreferencesAppSynchronize(BUNDLE_ID)

    except Exception:
        pass


def pref(pref_name):
    """Return a preference value.

    Since this uses CFPreferencesCopyAppValue, Preferences can be defined
    several places. Precedence is:
        - MCX
        - /var/root/Library/Preferences/com.salopensource.sal.plist
        - /Library/Preferences/com.salopensource.sal.plist
        - default_prefs defined here.
    """
    default_prefs = {
        'ServerURL': 'http://sal',
        'osquery_launchd': 'com.facebook.osqueryd.plist',
        'SkipFacts': [],
        'SyncScripts': True,
        'BasicAuth': True,
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
    cmd = [
        '/usr/bin/curl', '--silent', '--show-error', '--connect-timeout', '2']

    basic_auth = pref('BasicAuth')
    if basic_auth:
        key = pref('key')
        user_pass = 'sal:%s' % key
        cmd += ['--user', user_pass]

    max_time = '8' if data else '4'
    cmd += ['--max-time', max_time]

    if data:
        cmd += ['--data', data]

    cmd += [url]

    import pdb; pdb.set_trace()
    task = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = task.communicate()
    return stdout, stderr


def get_file_and_hash(path):
    """Given a filepath, return a tuple of (file contents, sha256."""
    text = ''
    if os.path.isfile(path):
        with open(path) as ifile:
            text = ifile.read()

    return (text, hashlib.sha256(text).hexdigest())


def dict_clean(items):
    result = {}
    skip_facts = pref('SkipFacts')
    for key, value in items:
        skip = False
        if value is None:
            value = 'None'

        for skip_fact in skip_facts:
            if key.startswith(skip_fact):
                skip = True
                break

        if skip == False:
            result[key] = value

    return result
