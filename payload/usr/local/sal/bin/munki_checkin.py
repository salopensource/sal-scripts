#!/usr/bin/python


import datetime
import os
import plistlib
import sys
from xml.parsers.expat import ExpatError

sys.path.append('/usr/local/munki')
from munkilib import munkicommon
sys.path.append('/usr/local/sal')
import utils


def main():
    munki_submission = {}
    munki_report = get_managed_install_report()

    munki_submission['munki_version'] = munki_report['MachineInfo'].get('munki_version')
    munki_submission['manifest'] = munki_report['ManifestName']

    munki_submission['facts'] = {}
    for condition, value in munki_report['Conditions'].items():
        # Join lists of strings into a comma-delimited string, as
        # the server wants just text.
        if hasattr(value, 'append'):
            value = ', '.join(value)
        munki_submission['facts'][condition] = value

    munki_submission['messages'] = []
    for key in ('Errors', 'Warnings'):
        for msg in munki_report[key]:
            munki_submission['messages'].append({'message_type': key, 'message': msg})

    # Process managed items and update histories.
    munki_submission['managed_items'] = {}
    munki_submission['update_history'] = {}
    for item in munki_report['ManagedInstalls']:
        name = item['name']
        submission_item = {}
        # TODO: Should we make this TZ aware?
        submission_item['date_managed'] = datetime.datetime.utcnow().isoformat()
        submission_item['status'] = 'PRESENT' if item['installed'] else 'ABSENT'
        # Pop off these two since we already used them.
        item.pop('name')
        item.pop('installed')
        item['type'] = 'ManagedInstalls'
        submission_item['data'] = item
        munki_submission['managed_items'][name] = submission_item

        # TODO: Process pending into UHI

    # TODO: Process InstallResults and RemovalResults into update history

    # TODO: AppleUpdates section -> UpdateHistory

    utils.add_checkin_results('munki', munki_submission)

    """
    'update_history': [  # Records to add to the Update Histories: pending, results of installs/removals, Apple or 3rd party
        {
            'update_type': 'str',  # (One of 'third_party', 'apple'),
            'name': 'str',
            'version': 'str',
            'date': '2019-02-01T13:00:00Z',  # UTC date time as str
            'status': 'str',  # One of ('pending', 'error', 'install', 'removal')
            'extra': 'str'
        },
        ...
    'managed_items': {  # ManagedInstalls, ManagedUninstalls
        '[item name]': {
            'date_managed': '2019-02-01T13:00:00Z',  # UTC datetime as str
            'status': 'str',  # See status choices
            'retention': bool,  # Whether to retain up to your retention period, or delete on checkin if absent.
            'data': {
                'key': 'value',  # Arbitrary key value pairs of additional information.
                'type': 'str'  # Munki ManagedItems must include the type of item: ManagedInstall, ManagedUninstall, OptionalInstall, etc.
                ...
            }
    """


def get_managed_install_report():
    """Return Munki ManagedInstallsReport.plist as a plist dict.

    Returns:
        ManagedInstalls report for last Munki run as a plist
        dict, or an empty dict.
    """
    # Checks munki preferences to see where the install directory is set to.
    managed_install_dir = munkicommon.pref('ManagedInstallDir')

    # set the paths based on munki's configuration.
    managed_install_report = os.path.join(managed_install_dir, 'ManagedInstallReport.plist')

    try:
        munki_report = plistlib.readPlist(managed_install_report)
    except (IOError, ExpatError):
        munki_report = {}

    if 'MachineInfo' not in munki_report:
        munki_report['MachineInfo'] = {}

    return munki_report


if __name__ == "__main__":
    main()
