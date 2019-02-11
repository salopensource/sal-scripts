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
    munki_submission['runtype'] = munki_report.get('RunType', 'custom')

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

    # TODO: Pull any histories that are sitting, waiting to be delivered to Sal in the
    # checkin_results and add onto them rather than start from scratch.
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    # Process managed items and update histories.
    munki_submission['managed_items'] = {}
    munki_submission['update_history'] = []

    for item in munki_report.get('ManagedInstalls', []):
        name = item['name']
        submission_item = {}
        submission_item['date_managed'] = now
        submission_item['status'] = 'PRESENT' if item['installed'] else 'ABSENT'
        # Pop off these two since we already used them.
        item.pop('name')
        item.pop('installed')
        item['type'] = 'ManagedInstalls'
        submission_item['data'] = item
        munki_submission['managed_items'][name] = submission_item

        if submission_item['status'] == 'ABSENT':
            # This is pending; put into update histories.
            history = {'name': name, 'update_type': 'third_party', 'status': 'pending'}
            history['date'] = now
            history['version'] = item['version_to_install']
            munki_submission['update_history'].append(history)

    # AppleUpdates section -> UpdateHistoryItem
    for item in munki_report.get('AppleUpdates', []):
        history = {'name': item['name'], 'update_type': 'apple', 'status': 'pending'}
        history['date'] = now
        history['version'] = item['version_to_install']
        # TODO: This won't do anything on the server yet.
        history['extra'] = item['productKey']
        munki_submission['update_history'].append(history)

    # Process InstallResults and RemovalResults into update history
    for report_key, result_type in (('InstallResults', 'install'), ('RemovalResults', 'removal')):
        for item in munki_report.get(report_key, []):
            history = {'name': item['name']}
            history['update_type'] = 'apple' if item.get('applesus') else 'third_party'
            history['version'] = item.get('version', '0')
            history['status'] = 'error' if item.get('status') != 0 else result_type
            # Munki puts a UTC time in, but python drops the TZ info.
            # Convert to the expected submission format of ISO in UTC.
            history['recorded'] = item['time'].isoformat() + 'Z'
            munki_submission['update_history'].append(history)


    utils.set_checkin_results('munki', munki_submission)


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
