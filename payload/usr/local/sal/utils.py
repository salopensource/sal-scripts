#!/usr/bin/python


import base64
import bz2
import datetime
import hashlib
import json
import os
import stat
import subprocess
import sys
import time
import urllib

sys.path.insert(0, '/usr/local/munki')
from munkilib import FoundationPlist
from Foundation import (kCFPreferencesAnyUser, kCFPreferencesCurrentHost, CFPreferencesSetValue,
                        CFPreferencesAppSynchronize, CFPreferencesCopyAppValue, NSDate, NSArray,
                        NSDictionary, NSData)


BUNDLE_ID = 'com.github.salopensource.sal'
RESULTS_PATH = '/usr/local/sal/checkin_results.json'
VERSION = '3.0.5'


def sal_version():
    return VERSION


def set_pref(pref_name, pref_value):
    """Sets a Sal preference.

    The preference file on disk is located at
    /Library/Preferences/com.github.salopensource.sal.plist.  This should
    normally be used only for 'bookkeeping' values; values that control
    the behavior of munki may be overridden elsewhere (by MCX, for
    example)"""
    try:
        CFPreferencesSetValue(
            pref_name, pref_value, BUNDLE_ID, kCFPreferencesAnyUser, kCFPreferencesCurrentHost)
        CFPreferencesAppSynchronize(BUNDLE_ID)

    except Exception:
        pass


def pref(pref_name, default=None):
    """Return a preference value.

    Since this uses CFPreferencesCopyAppValue, Preferences can be defined
    several places. Precedence is:
        - MCX
        - /var/root/Library/Preferences/com.github.salopensource.sal.plist
        - /Library/Preferences/com.github.salopensource.sal.plist
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
        'LastRunWasOffline': False,
        'SendOfflineReport': False,
    }

    pref_value = CFPreferencesCopyAppValue(pref_name, BUNDLE_ID)
    if pref_value is None and default:
        pref_value = default
    elif pref_value is None and pref_name in default_prefs:
        pref_value = default_prefs.get(pref_name)
        # we're using a default value. We'll write it out to
        # /Library/Preferences/<BUNDLE_ID>.plist for admin
        # discoverability
        set_pref(pref_name, pref_value)

    if isinstance(pref_value, NSDate):
        # convert NSDate/CFDates to strings
        pref_value = str(pref_value)

    return pref_value


def python_script_running(scriptname):
    """Tests if a script is running.

    If it is found running, it will try up to two more times to see if it has exited.
    """
    counter = 0
    pid = 0
    while True:
        if counter == 3:
            return pid
        pid = check_script_running(scriptname)
        if not pid:
            return pid
        else:
            time.sleep(1)
            counter = counter + 1


def check_script_running(scriptname):
    """
    Returns Process ID for a running python script.
    Not at all stolen from Munki. Honest.
    """
    cmd = ['/bin/ps', '-eo', 'pid=,command=']
    proc = subprocess.Popen(cmd, shell=False, bufsize=1,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, dummy_err) = proc.communicate()
    mypid = os.getpid()
    lines = str(out).splitlines()
    for line in lines:
        try:
            (pid, process) = line.split(None, 1)
        except ValueError:
            # funky process line, so we'll skip it
            pass
        else:
            args = process.split()
            try:
                # first look for Python processes
                if (args[0].find('MacOS/Python') != -1 or
                        args[0].find('python') != -1):
                    # look for first argument being scriptname
                    if args[1].find(scriptname) != -1:
                        try:
                            if int(pid) != int(mypid):
                                return pid
                        except ValueError:
                            # pid must have some funky characters
                            pass
            except IndexError:
                pass
    # if we get here we didn't find a Python script with scriptname
    # (other than ourselves)
    return 0


def curl(url, data=None, json_path=None):
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

    if VERSION:
        cmd += ['--header', 'SalScript-Version: %s' % VERSION]

    if data:
        cmd += ['--data', data]
    elif json_path:
        cmd += ['--header', 'Content-Type: application/json']
        # Use the @ syntax for curl to open the file and do any required
        # encoding for us.
        cmd += ['--data', '@%s' % json_path]

    cmd.append(url)

    task = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return task.communicate()


def get_file_and_hash(path):
    """Given a filepath, return a tuple of (file contents, sha256."""
    text = ''
    if os.path.isfile(path):
        with open(path) as ifile:
            text = ifile.read()

    return text, hashlib.sha256(text).hexdigest()


def send_report(url, form_data=None, json_data=None, json_path=None):
    if form_data:
        stdout, stderr = curl(url, data=urllib.urlencode(form_data))
    elif json_data:
        raise NotImplementedError
    elif json_path:
        stdout, stderr = curl(url, json_path=RESULTS_PATH)

    return stdout, stderr


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


def get_checkin_results():
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH) as results_handle:
            results = json.load(results_handle)
    else:
        results = {}

    return results


def clean_results():
    os.remove(RESULTS_PATH)


def save_results(data):
    """Replace all data in the results file."""
    with open(RESULTS_PATH, 'w') as results_handle:
        # Python2 json.dump encodes all unicode to UTF-8 for us.
        json.dump(data, results_handle, default=serializer)


def set_checkin_results(module_name, data):
    """Set data by name to the shared results JSON file.

    Existing data is overwritten.

    Args:
        module_name (str): Name of the management source returning data.
        data (dict): Dictionary of results.
    """
    results = get_checkin_results()

    results[module_name] = data
    save_results(results)


def serializer(obj):
    """Func used by `json.dump`s default arg to serialize datetimes."""
    # Through testing, it seems that this func is not used by json.dump
    # for strings, so we don't have to handle them here.
    if isinstance(obj, datetime.datetime):
        obj = obj.isoformat() + 'Z'
    return obj


def run_scripts(dir_path, cli_args=None, error=False):
    results = []
    for script in os.listdir(dir_path):
        script_stat = os.stat(os.path.join(dir_path, script))
        if not script_stat.st_mode & stat.S_IWOTH:
            cmd = [os.path.join(dir_path, script)]
            if cli_args:
                cmd.append(cli_args)
            try:
                subprocess.check_call(cmd, stdin=None)
                results.append("'{}' ran successfully".format(script))
            except (OSError, subprocess.CalledProcessError):
                errormsg = "'{}' had errors during execution!".format(script)
                if not error:
                    results.append(errormsg)
                else: 
                    raise RuntimeError(errormsg) 
        else:
            results.append("'{}' is not executable or has bad permissions".format(script))
    return results


def get_server_prefs():
    """Get Sal preferences, bailing if required info is missing.

    Returns:
        Tuple of (Server URL, NameType, and key (business unit key)
    """
    # Check for mandatory prefs and bail if any are missing.
    required_prefs = {
        'key': pref('key'),
        'server_url': pref('ServerURL').rstrip('/')}

    for key, val in required_prefs.items():
        if not val:
            sys.exit('Required Sal preference "{}" is not set.'.format(key))

    # Get optional preferences.
    name_type = pref('NameType', default='ComputerName')

    return required_prefs["server_url"], name_type, required_prefs["key"]


def unobjctify(plist_data):
    """Recursively convert pyobjc types to native python"""
    if isinstance(plist_data, NSArray):
        return [unobjctify(i) for i in plist_data]
    elif isinstance(plist_data, NSDictionary):
        return {k: unobjctify(v) for k, v in plist_data.items()}
    elif isinstance(plist_data, NSData):
        return u'<RAW DATA>'
    elif isinstance(plist_data, NSDate):
        # NSDate.description is in UTC, so drop the offset and we'll
        # add it back in when serializing to JSON.
        date_as_iso_string = plist_data.description().rsplit(' ', 1)[0]
        return datetime.datetime.strptime(date_as_iso_string, '%Y-%m-%d %H:%M:%S')
    # bools, floats, and ints seem to be covered.
    return plist_data


def submission_encode(text):
    """Return a b64 encoded, bz2 compressed copy of text."""
    return base64.b64encode(bz2.compress(text))
