#!/usr/bin/python


import base64
import binascii
import bz2
import datetime
import hashlib
import json
import logging
import os
import pathlib
import plistlib
import stat
import subprocess
import time
import urllib.parse

import macsesh
from Foundation import (
    kCFPreferencesAnyUser, kCFPreferencesCurrentHost, CFPreferencesSetValue,
    CFPreferencesAppSynchronize, CFPreferencesCopyAppValue, CFPreferencesAppValueIsForced, NSDate,
    NSArray, NSDictionary, NSData, NSNull)

import sal.version


BUNDLE_ID = 'com.github.salopensource.sal'
RESULTS_PATH = '/usr/local/sal/checkin_results.json'
ISO_TIME_FORMAT = '%Y-%m-%d %H:%M:%S %z'


def set_pref(pref_name, pref_value):
    """Sets a Sal preference.

    The preference file on disk is located at
    /Library/Preferences/com.github.salopensource.sal.plist.  This should
    normally be used only for 'bookkeeping' values; values that control
    the behavior of munki may be overridden elsewhere (by MCX, for
    example)
    """
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

    Returned values are all converted to native python types through the
    `unobjctify` function; e.g. dates are returned as aware-datetimes,
    NSDictionary to dict, etc.
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
    if pref_value is None and default is not None:
        pref_value = default
    elif pref_value is None and pref_name in default_prefs:
        pref_value = default_prefs.get(pref_name)
        # we're using a default value. We'll write it out to
        # /Library/Preferences/<BUNDLE_ID>.plist for admin
        # discoverability
        set_pref(pref_name, pref_value)

    return unobjctify(pref_value)


def prefs():
    prefs = (
        'ServerURL', 'key', 'BasicAuth', 'SyncScripts', 'SkipFacts', 'CACert', 'SendOfflineReport',
        'SSLClientCertificate', 'SSLClientKey', 'MessageBlacklistPatterns')
    return {k: {'value': pref(k), 'forced': forced(k)} for k in prefs}


def forced(pref):
    return CFPreferencesAppValueIsForced(pref, BUNDLE_ID)


def wait_for_script(scriptname, repeat=3, pause=1):
    """Tries a few times to wait for a script to finish."""
    count = 0
    while count < repeat:
        if script_is_running(scriptname):
            time.sleep(pause)
            count += 1
        else:
            return False
    return True


def script_is_running(scriptname):
    """Returns Process ID for a running python script.

    Not at all stolen from Munki. Honest.
    """
    cmd = ['/bin/ps', '-eo', 'pid=,command=']
    proc = subprocess.Popen(
        cmd, bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, _ = proc.communicate()
    mypid = os.getpid()
    for line in out.splitlines():
        try:
            pid, process = line.split(maxsplit=1)
        except ValueError:
            # funky process line, so we'll skip it
            pass
        else:
            args = process.split()
            try:
                # first look for Python processes
                if 'MacOS/Python' in args[0] or 'python' in args[0]:
                    # look for first argument being scriptname
                    if scriptname in args[1]:
                        try:
                            if int(pid) != mypid:
                                return True
                        except ValueError:
                            # pid must have some funky characters
                            pass
            except IndexError:
                pass

    # if we get here we didn't find a Python script with scriptname
    # (other than ourselves)
    return False


def get_hash(file_path):
    """Return sha256 hash of file_path."""
    text = b''
    if (path := pathlib.Path(file_path)).is_file():
        text = path.read_bytes()
    return hashlib.sha256(text).hexdigest()


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
    plist_path = pathlib.Path('/usr/local/sal/plugin_results.plist')
    if plist_path.exists():
        plugin_results = plistlib.loads(plist_path.read_bytes())
    else:
        plugin_results = []

    plugin_results.append({'plugin': plugin, 'historical': historical, 'data': data})
    plist_path.write_bytes(plistlib.dumps(plugin_results))


def get_checkin_results():
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH) as results_handle:
            try:
                results = json.load(results_handle)
            except json.decoder.JSONDecodeError:
                results = {}
    else:
        results = {}

    return results


def clean_results():
    os.remove(RESULTS_PATH)


def save_results(data):
    """Replace all data in the results file."""
    with open(RESULTS_PATH, 'w') as results_handle:
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
        # Make sure everything has been set to offset 0 / UTC time.
        obj = obj.astimezone(datetime.timezone.utc).isoformat()
    return obj


def run_scripts(dir_path, cli_args=None, error=False):
    results = []
    skip_names = {'__pycache__'}
    scripts = (p for p in pathlib.Path(dir_path).iterdir() if p.name not in skip_names)
    for script in scripts:
        if script.stat().st_mode & stat.S_IWOTH:
            results.append(f"'{script}' is not executable or has bad permissions")
            continue

        cmd = [script]
        if cli_args:
            cmd.append(cli_args)
        try:
            subprocess.check_call(cmd)
            results.append(f"'{script}' ran successfully")
        except (OSError, subprocess.CalledProcessError):
            errormsg = f"'{script}' had errors during execution!"
            if not error:
                results.append(errormsg)
            else:
                raise RuntimeError(errormsg)

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
            exit(f'Required Sal preference "{key}" is not set.')

    # Get optional preferences.
    name_type = pref('NameType', default='ComputerName')

    return required_prefs["server_url"], name_type, required_prefs["key"]


def unobjctify(element, safe=False):
    """Recursively convert nested elements to native python datatypes.

    Types accepted include str, bytes, int, float, bool, None, list,
    dict, set, tuple, NSArray, NSDictionary, NSData, NSDate, NSNull.

    element: Some (potentially) nested data you want to convert.

    safe: Bool (defaults to False) whether you want printable
        representations instead of the python equivalent. e.g.  NSDate
        safe=True becomes a str, safe=False becomes a datetime.datetime.
        NSData safe=True bcomes a hex str, safe=False becomes bytes. Any
        type not explicitly handled by this module will raise an
        exception unless safe=True, where it will instead replace the
        data with a str of '<UNSUPPORTED TYPE>'

        This is primarily for safety in serialization to plists or
        output.

    returns: Python equivalent of the original input.
        e.g. NSArray -> List, NSDictionary -> Dict, etc.

    raises: ValueError for any data that isn't supported (yet!) by this
        function.
    """
    supported_types = (str, bytes, int, float, bool, datetime.datetime)
    if isinstance(element, supported_types):
        return element
    elif isinstance(element, (dict, NSDictionary)):
        return {k: unobjctify(v, safe=safe) for k, v in element.items()}
    elif isinstance(element, (list, NSArray)):
        return [unobjctify(i, safe=safe) for i in element]
    elif isinstance(element, set):
        return set([unobjctify(i, safe=safe) for i in element])
    elif isinstance(element, tuple):
        return tuple([unobjctify(i, safe=safe) for i in element])
    elif isinstance(element, NSData):
        return binascii.hexlify(element) if safe else bytes(element)
    elif isinstance(element, NSDate):
        return str(element) if safe else datetime.datetime.strptime(
            element.description(), ISO_TIME_FORMAT)
    elif isinstance(element, NSNull) or element is None:
        return '' if safe else None
    elif safe:
        return '<UNSUPPORTED TYPE>'
    raise ValueError(f"Element type '{type(element)}' is not supported!")


def submission_encode(data: bytes) -> bytes:
    """Return a b64 encoded, bz2 compressed copy of text."""
    return base64.b64encode(bz2.compress(data))
