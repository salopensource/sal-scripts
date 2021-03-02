#!/usr/bin/python


import base64
import bz2
import datetime
import hashlib
import json
import os
import platform
import pathlib
import plistlib


RESULTS_PATH = {"Darwin": "/usr/local/sal/checkin_results.json"}.get(platform.system())


def get_hash(file_path):
    """Return sha256 hash of file_path."""
    text = b""
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
    if platform.system() == "Darwin":
        plist_path = pathlib.Path("/usr/local/sal/plugin_results.plist")
    else:
        raise NotImplementedError("Please PR a plugin results path for your platform!")
    if plist_path.exists():
        plugin_results = plistlib.loads(plist_path.read_bytes())
    else:
        plugin_results = []

    plugin_results.append({"plugin": plugin, "historical": historical, "data": data})
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
    with open(RESULTS_PATH, "w") as results_handle:
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


def submission_encode(data: bytes) -> bytes:
    """Return a b64 encoded, bz2 compressed copy of text."""
    return base64.b64encode(bz2.compress(data))
