import binascii
import datetime
import logging
import os
import pathlib
import subprocess
import time

from Foundation import (
    kCFPreferencesAnyUser, kCFPreferencesCurrentHost, CFPreferencesSetValue,
    CFPreferencesAppSynchronize, CFPreferencesCopyAppValue, CFPreferencesAppValueIsForced, NSDate,
    NSArray, NSDictionary, NSData, NSNull)

from sal.client import get_sal_client, MacKeychainClient


BUNDLE_ID = 'com.github.salopensource.sal'
ISO_TIME_FORMAT = '%Y-%m-%d %H:%M:%S %z'


def setup_sal_client():
    ca_cert = sal_pref('CACert', '')
    cert = sal_pref('SSLClientCertificate', '')
    key = sal_pref('SSLClientKey', '')
    exists = map(os.path.exists, (ca_cert, cert, key))
    if any(exists):
        if not all(exists):
            logging.warning(
                'Argument warning! If using the `CACert`, `SSLClientCertificate`, or '
                '`SSLClientKey` prefs, they must all be either paths to cert files or the '
                'common name of the certs to find in the keychain.')

        # If any of the above have been passed as a path, we have to
        # use a vanilla Session.
        logging.debug('Using SalClient')
        client = get_sal_client()
    else:
        # Assume that any passed certs are by CN since they don't
        # exist as files anywhere.
        # If we're going to use the keychain, we need to use a
        # macsesh
        logging.debug('Using MacKeychainClient')
        client = get_sal_client(MacKeychainClient)

    if ca_cert:
        client.verify = ca_cert
    if cert:
        client.cert = (cert, key) if key else cert

    basic_auth = sal_pref('BasicAuth')
    if basic_auth:
        key = sal_pref('key', '')
        client.auth = ('sal', key)

    client.base_url = sal_pref('ServerURL')


def mac_pref(domain, key, default=None):
    val = CFPreferencesCopyAppValue(key, domain)
    return val if val is not None else default


def set_sal_pref(pref_name, pref_value):
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


def sal_pref(pref_name, default=None):
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

    pref_value = mac_pref(BUNDLE_ID, pref_name, default)
    if pref_value is None and pref_name in default_prefs:
        # If we got here, the pref value was either set to None or never
        # set, AND the default was also None. Fall back to auto prefs.
        pref_value = default_prefs.get(pref_name)
        # we're using a default value. We'll write it out to
        # /Library/Preferences/<BUNDLE_ID>.plist for admin
        # discoverability
        set_sal_pref(pref_name, pref_value)

    return unobjctify(pref_value)


def forced(pref, bundle_identifier=BUNDLE_ID):
    return CFPreferencesAppValueIsForced(pref, bundle_identifier)


def prefs_report():
    prefs = (
        'ServerURL', 'key', 'BasicAuth', 'SyncScripts', 'SkipFacts', 'CACert', 'SendOfflineReport',
        'SSLClientCertificate', 'SSLClientKey', 'MessageBlacklistPatterns')
    return {k: {'value': sal_pref(k), 'forced': forced(k)} for k in prefs}


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
        return {unobjctify(i, safe=safe) for i in element}
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


def run_scripts(dir_path, cli_args=None, error=False):
    results = []
    skip_names = {'__pycache__'}
    scripts = (p for p in pathlib.Path(dir_path).iterdir() if p.name not in skip_names)
    for script in scripts:
        if not os.access(script, os.X_OK):
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

