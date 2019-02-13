#!/usr/bin/python


import datetime
import os
import sys

sys.path.append('/usr/local/munki')
from munkilib import FoundationPlist, munkicommon
sys.path.append('/usr/local/sal')
import utils


__version__ = '1.0.0'


def main():
    # If we haven't successfully submitted to Sal, pull the existing
    # munki section rather than start from scratch, as we want to
    # keep any install/removal history that may be there.
    munki_submission = utils.get_checkin_results().get('munki', {})
    munki_report = get_managed_install_report()

    munki_submission['munki_version'] = munki_report['MachineInfo'].get('munki_version')
    munki_submission['manifest'] = munki_report['ManifestName']
    munki_submission['runtype'] = munki_report.get('RunType', 'custom')

    munki_submission['facts'] = {'facts': {'checkin_module_version': __version__}}
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

    now = datetime.datetime.utcnow().isoformat() + 'Z'
    # Process managed items and update histories.
    munki_submission['managed_items'] = {}

    if 'update_history' not in munki_submission:
        munki_submission['update_history'] = []

    optional_manifest = get_optional_manifest()

    for item in munki_report.get('ManagedInstalls', []):
        name = item['name']
        submission_item = {}
        submission_item['date_managed'] = now
        submission_item['status'] = 'PRESENT' if item['installed'] else 'ABSENT'
        # Pop off these two since we already used them.
        item.pop('name')
        item.pop('installed')
        item['type'] = 'ManagedInstalls'
        self_serve = 'True' if name in optional_manifest.get('managed_installs', []) else 'False'
        item['self_serve'] = self_serve
        submission_item['data'] = item
        munki_submission['managed_items'][name] = submission_item

        if submission_item['status'] == 'ABSENT':
            # This is pending; put into update histories.
            history = {'name': name, 'update_type': 'third_party', 'status': 'pending'}
            history['date'] = now
            history['version'] = item['version_to_install']
            munki_submission['update_history'].append(history)

    for item in munki_report.get('managed_uninstalls_list', []):
        submission_item = {'date_managed': now, 'status': 'ABSENT'}
        self_serve = 'True' if name in optional_manifest.get('managed_uninstalls', []) else 'False'
        submission_item['data'] = {'self_serve': self_serve, 'type': 'ManagedUninstalls'}
        munki_submission['managed_items'][item] = submission_item

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
            history['date'] = item['time'].isoformat() + 'Z'
            # Only add if there isn't already an identical one waiting
            # to be sent.
            if history not in munki_submission['update_history']:
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
        munki_report = FoundationPlist.readPlist(managed_install_report)
    except (IOError, FoundationPlist.NSPropertyListSerializationException):
        munki_report = {}

    if 'MachineInfo' not in munki_report:
        munki_report['MachineInfo'] = {}

    return utils.unobjctify(munki_report)


def get_optional_manifest():
    """Return Munki SelfServeManifest as a plist dict.

    Returns:
        SelfServeManifest for last Munki run as a plist
        dict, or an empty dict.
    """
    # Checks munki preferences to see where the install directory is set to.
    managed_install_dir = munkicommon.pref('ManagedInstallDir')

    # set the paths based on munki's configuration.
    optional_manifest_path = os.path.join(managed_install_dir, 'manifests/SelfServeManifest')

    try:
        optional_manifest = FoundationPlist.readPlist(optional_manifest_path)
    except (IOError, FoundationPlist.NSPropertyListSerializationException):
        optional_manifest = {}

    return optional_manifest


if __name__ == "__main__":
    main()
