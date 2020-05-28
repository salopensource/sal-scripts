#!/usr/bin/python


import base64
import binascii
import bz2
import datetime
import hashlib
import json
import os
import pathlib
import plistlib
import subprocess
import time


RESULTS_PATH = '/usr/local/sal/checkin_results.json'


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


def submission_encode(data: bytes) -> bytes:
    """Return a b64 encoded, bz2 compressed copy of text."""
    return base64.b64encode(bz2.compress(data))
