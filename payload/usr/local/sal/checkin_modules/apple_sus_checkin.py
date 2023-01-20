#!/usr/local/sal/Python.framework/Versions/Current/bin/python3


import datetime
import os
import pathlib
import platform
import plistlib
import re
import subprocess
from distutils.version import StrictVersion

import sal


__version__ = "1.2.0"


def main():
    sus_submission = {}
    sus_submission["facts"] = get_sus_facts()

    # Process managed items and update histories.
    sus_submission["managed_items"] = get_sus_install_report()
    sus_submission["update_history"] = []

    pending = get_pending()
    sus_submission["managed_items"].update(pending)

    sal.set_checkin_results("Apple Software Update", sus_submission)


def get_sus_install_report():
    """Return installed apple updates from softwareupdate"""
    try:
        history = plistlib.loads(
            pathlib.Path("/Library/Receipts/InstallHistory.plist").read_bytes()
        )
    except (IOError, plistlib.InvalidFileException):
        history = []
    return {
        i["displayName"]: {
            "date_managed": i["date"],
            "status": "PRESENT",
            "data": {
                "type": "Apple SUS Install",
                "version": i["displayVersion"].strip(),
            },
        }
        for i in history
        if i["processName"] == "softwareupdated"
    }


def get_sus_facts():
    result = {"checkin_module_version": __version__}
    history_limit = datetime.datetime.now().astimezone(
        datetime.timezone.utc
    ) - datetime.timedelta(days=1)
    cmd = ["softwareupdate", "--dump-state"]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        return result

    with open("/var/log/install.log") as handle:
        install_log = handle.readlines()

    for line in reversed(install_log):
        # TODO: Stop if we go before the subprocess call datetime-wise
        if "Catalog: http" in line and "catalog" not in result:
            result["catalog"] = line.split()[-1]
        elif "SUScan: Elapsed scan time = " in line and "last_check" not in result:
            result["last_check"] = _get_log_time(line).isoformat()

        if (log_time := _get_log_time(line)) and log_time < history_limit:
            # Let's not look earlier than when we started
            # softwareupdate.
            break

        elif "catalog" in result and "last_check" in result:
            # Once we have both facts, bail; no need to process the
            # entire file.
            break

    return result


def _get_log_time(line):
    # Example date 2019-02-08 10:49:56-05
    raw_datetime = " ".join(line.split()[:2])
    # Add 0's to make TZ offset work with strptime (expects a 4
    # digit offset). This should hopefully cover even those off
    # by minutes locations. e.g. I would hope the above log time in
    # French Polynesia would look like this: 2019-02-08 10:49:56-0930
    raw_datetime += (24 - len(raw_datetime)) * "0"

    try:
        aware_datetime = datetime.datetime.strptime(raw_datetime, "%Y-%m-%d %H:%M:%S%z")
    except ValueError:
        aware_datetime = None
    # Convert to UTC time.
    return (
        None if not aware_datetime else aware_datetime.astimezone(datetime.timezone.utc)
    )


def get_pending():
    if os.path.exists("/Library/Preferences/com.apple.SoftwareUpdate.plist"):
        pending_items = get_pending_updates_from_preferences()
        if pending_items != None:
            return pending_items

    pending_items = {}
    cmd = ["softwareupdate", "-l", "--no-scan"]
    try:
        # softwareupdate outputs "No new software available" to stderr,
        # so we pipe it off.
        output = subprocess.check_output(cmd, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError:
        return pending_items

    # The following regex code is from Shea Craig's work on the Salt
    # mac_softwareupdate module. Reference that for future updates.
    if StrictVersion(platform.mac_ver()[0]) >= StrictVersion("10.15"):
        # Example output:
        # Software Update Tool
        #
        # Finding available software
        # Software Update found the following new or updated software:
        # * Label: Command Line Tools beta 5 for Xcode-11.0
        #     Title: Command Line Tools beta 5 for Xcode, Version: 11.0, Size: 224804K, Recommended: YES,
        # * Label: macOS Catalina Developer Beta-6
        #     Title: macOS Catalina Public Beta, Version: 5, Size: 3084292K, Recommended: YES, Action: restart,
        # * Label: BridgeOSUpdateCustomer
        #     Title: BridgeOSUpdateCustomer, Version: 10.15.0.1.1.1560926689, Size: 390674K, Recommended: YES, Action: shut down,
        # - Label: iCal-1.0.2
        #     Title: iCal, Version: 1.0.2, Size: 6520K,
        rexp = re.compile(
            r"(?m)"  # Turn on multiline matching
            r"^\s*[*-] Label: "  # Name lines start with * or - and "Label: "
            r"(?P<name>[^ ].*)[\r\n]"  # Capture the rest of that line; this is the update name.
            r".*Version: (?P<version>[^,]*), "  # Grab the version number.
            r"Size: (?P<size>[^,]*),\s*"  # Grab the size; unused at this time.
            r"(?P<recommended>Recommended: YES,)?\s*"  # Optionally grab the recommended flag.
            r"(?P<action>Action: (?:restart|shut down),)?"  # Optionally grab an action.
        )
    else:
        # Example output:
        # Software Update Tool
        #
        # Finding available software
        # Software Update found the following new or updated software:
        #    * Command Line Tools (macOS Mojave version 10.14) for Xcode-10.3
        #        Command Line Tools (macOS Mojave version 10.14) for Xcode (10.3), 199140K [recommended]
        #    * macOS 10.14.1 Update
        #        macOS 10.14.1 Update (10.14.1), 199140K [recommended] [restart]
        #    * BridgeOSUpdateCustomer
        #        BridgeOSUpdateCustomer (10.14.4.1.1.1555388607), 328394K, [recommended] [shut down]
        #    - iCal-1.0.2
        #        iCal, (1.0.2), 6520K
        rexp = re.compile(
            r"(?m)"  # Turn on multiline matching
            r"^\s+[*-] "  # Name lines start with 3 spaces and either a * or a -.
            r"(?P<name>.*)[\r\n]"  # The rest of that line is the name.
            r".*\((?P<version>[^ \)]*)"  # Capture the last parenthesized value on the next line.
            r"[^\r\n\[]*(?P<recommended>\[recommended\])?\s?"  # Capture [recommended] if there.
            r"(?P<action>\[(?:restart|shut down)\])?"  # Capture an action if present.
        )

    # Convert local time to UTC time represented as a ISO 8601 str.
    now = datetime.datetime.now().astimezone(datetime.timezone.utc).isoformat()
    return {
        m.group("name"): {
            "date_managed": now,
            "status": "PENDING",
            "data": {
                "version": m.group("version"),
                "recommended": "TRUE"
                if "recommended" in m.group("recommended")
                else "FALSE",
                "action": _bracket_cleanup(m, "action"),
                "type": "Apple SUS Install",
            },
        }
        for m in rexp.finditer(output)
    }


def get_pending_updates_from_preferences():
    pending = {}
    try:
        pref = plistlib.loads(
            pathlib.Path(
                "/Library/Preferences/com.apple.SoftwareUpdate.plist"
            ).read_bytes()
        )
    except (IOError, plistlib.InvalidFileException):
        return None

    recommended_updates = pref.get("RecommendedUpdates", None)
    if not recommended_updates:
        return pending

    # Convert local time to UTC time represented as a ISO 8601 str.
    now = datetime.datetime.now().astimezone(datetime.timezone.utc).isoformat()
    for update in recommended_updates:
        name = update.get("Display Name")
        version = update.get("Display Version")
        item = {}
        item["date_managed"] = now
        item["status"] = "PENDING"
        item["data"] = {
            "version": version,
            "recommended": "TRUE",
            "type": "Apple SUS Install",
        }
        pending[name] = item
    return pending


def _bracket_cleanup(match, key):
    """Strip out [ and ] and uppercase SUS output"""
    return re.sub(r"[\[\]]", "", match.group(key) or "").upper()


if __name__ == "__main__":
    main()
