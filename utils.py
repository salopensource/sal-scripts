#!/usr/bin/python


import hashlib
import os
import stat
import subprocess
import sys

sys.path.append('/usr/local/munki')
from munkilib import FoundationPlist
from Foundation import kCFPreferencesAnyUser, \
                       kCFPreferencesCurrentHost, \
                       CFPreferencesSetValue, \
                       CFPreferencesAppSynchronize, \
                       CFPreferencesCopyAppValue, \
                       NSDate, NSArray


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
        'GetGrains': False,
        'GetOhai': False,
    }

    pref_value = CFPreferencesCopyAppValue(pref_name, BUNDLE_ID)
    if pref_value == None and pref_name in default_prefs:
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
    cmd = ['/usr/bin/curl', '--silent', '--show-error', '--connect-timeout', '2']

    # Use a PEM format certificate file to verify the peer. This is
    # useful primarily to support self-signed certificates, which are
    # rejected on 10.13's bundled curl. In cases where you have a cert
    # signed by an internal or external trusted CA, curl will happily
    # use the keychain.
    ca_cert = pref('CACert')
    if ca_cert:
        cmd += ['--cacert', ca_cert]

    basic_auth = pref('BasicAuth')
    if basic_auth:
        key = pref('key')
        user_pass = 'sal:%s' % key
        cmd += ['--user', user_pass]

    ssl_client_cert = pref('SSLClientCertificate')
    ssl_client_key = pref('SSLClientKey')
    if ssl_client_cert:
        cmd += ['--cert', ssl_client_cert]
        if ssl_client_key:
            cmd += ['--key', ssl_client_key]

    max_time = '8' if data else '4'
    cmd += ['--max-time', max_time]

    if data:
        cmd += ['--data', data]

    cmd += [url]

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


def add_plugin_results(plugin, data, historical=False):
    """Add data to the shared plugin results plist.

    This function creates the shared results plist file if it does not
    already exist; otherwise, it adds the entry by appending.

    Args:
        plugin (str): Name of the plugin returning data.
        data (dict): Dictionary of results.
        historical (bool): Whether to keep only one record (False) or
            all results (True). Optional, defaults to False.
    """
    plist_path = '/usr/local/sal/plugin_results.plist'
    if os.path.exists(plist_path):
        plugin_results = FoundationPlist.readPlist(plist_path)
    else:
        plugin_results = []

    plugin_results.append({'plugin': plugin, 'historical': historical, 'data': data})
    FoundationPlist.writePlist(plugin_results, plist_path)


def run_scripts(dir_path, cli_args):
    for script in os.listdir(dir_path):
        script_stat = os.stat(os.path.join(dir_path, script))
        if not script_stat.st_mode & stat.S_IWOTH:
            try:
                subprocess.call([os.path.join(dir_path, script), cli_args, stdin=None)
            except (OSError, subprocess.CalledProcessError):
                print "'{}' had errors during execution!".format(script)
        else:
            print "'{}' is not executable or has bad permissions".format(script)
