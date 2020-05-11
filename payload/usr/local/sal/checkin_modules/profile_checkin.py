#!/usr/local/sal/Python.framework/Versions/3.8/bin/python3


import datetime
import pathlib
import os
import plistlib
import subprocess
import sys
import tempfile

import sal
sys.path.insert(0, '/usr/local/munki')


__version__ = '1.0.0'


def main():
    profiles = get_profiles()
    submission = {}
    submission['facts'] = {'checkin_module_version': __version__}
    submission['managed_items'] = {}
    for profile in profiles.get('_computerlevel', []):
        name = profile['ProfileDisplayName']
        submission_item = {}
        submission_item['name'] = name
        submission_item['date_managed'] = profile['ProfileInstallDate']
        submission_item['status'] = 'PRESENT'

        data = {'profile_items': profile['ProfileItems']}
        data['profile_description'] = profile.get('ProfileDescription', '')
        data['identifier'] = profile['ProfileIdentifier']
        data['organization'] = profile['ProfileOrganization']
        data['uuid'] = profile['ProfileUUID']
        data['verification_state'] = profile.get('ProfileVerificationState', '')
        submission_item['data'] = data

        submission['managed_items'][name] = submission_item

    sal.set_checkin_results('Profiles', submission)
    # # If we haven't successfully submitted to Sal, pull the existing
    # # munki section rather than start from scratch, as we want to
    # # keep any install/removal history that may be there.
    # munki_submission = sal.get_checkin_results().get('munki', {})
    # munki_report = get_managed_install_report()

    # extras = {}
    # extras['munki_version'] = munki_report['MachineInfo'].get('munki_version')
    # extras['manifest'] = munki_report.get('ManifestName')
    # extras['runtype'] = munki_report.get('RunType', 'custom')

    # munki_submission['extra_data'] = extras

    # munki_submission['facts'] = {
    #     'checkin_module_version': __version__,
    #     'RunType': munki_report['RunType'],
    #     'StartTime': munki_report['StartTime'],
    #     'EndTime': munki_report['EndTime'],
    # }
    # if munki_report.get('Conditions'):
    #     for condition, value in munki_report['Conditions'].items():
    #         # Join lists of strings into a comma-delimited string, as
    #         # the server wants just text.
    #         if hasattr(value, 'append'):
    #             value = ', '.join(value)
    #         munki_submission['facts'][condition] = value

    # munki_submission['messages'] = []
    # for key in ('Errors', 'Warnings'):
    #     for msg in munki_report[key]:
    #         # We need to drop the final 'S' to match Sal's message types.
    #         munki_submission['messages'].append({'message_type': key.upper()[:-1], 'text': msg})

    # now = datetime.datetime.now().astimezone(datetime.timezone.utc).isoformat()
    # # Process managed items and update histories.
    # munki_submission['managed_items'] = {}

    # optional_manifest = get_optional_manifest()

    # for item in munki_report.get('ManagedInstalls', []):
    #     submission_item = {'date_managed': now}
    #     submission_item['status'] = 'PRESENT' if item['installed'] else 'PENDING'

    #     version_key = 'version_to_install' if not item['installed'] else 'installed_version'
    #     version = item[version_key]
    #     name = f'{item["name"]} {version}'
    #     submission_item['name'] = name

    #     # Pop off these two since we already used them.
    #     item.pop('name')
    #     item.pop('installed')

    #     item['type'] = 'ManagedInstalls'
    #     self_serve = 'True' if name in optional_manifest.get('managed_installs', []) else 'False'
    #     item['self_serve'] = self_serve
    #     submission_item['data'] = item
    #     munki_submission['managed_items'][name] = submission_item

    # for item in munki_report.get('managed_uninstalls_list', []):
    #     submission_item = {'date_managed': now, 'status': 'ABSENT'}
    #     self_serve = 'True' if name in optional_manifest.get('managed_uninstalls', []) else 'False'
    #     submission_item['data'] = {'self_serve': self_serve, 'type': 'ManagedUninstalls'}
    #     munki_submission['managed_items'][item] = submission_item

    # # Process InstallResults and RemovalResults into update history
    # for report_key in ('InstallResults', 'RemovalResults'):
    #     for item in munki_report.get(report_key, []):
    #         # Skip Apple software update items.
    #         if item.get('applesus'):
    #             continue
    #         # Construct key; we pop the name off because we don't need
    #         # to submit it again when we stuff `item` into `data`.
    #         name = f'{item.pop("name")} {item["version"]}'
    #         submission_item = munki_submission['managed_items'].get(name, {'name': name})
    #         if item.get('status') != 0:
    #             # Something went wrong, so change the status.
    #             submission_item['status'] = 'ERROR'
    #         if 'data' in submission_item:
    #             submission_item['data'].update(item)
    #         else:
    #             submission_item['data'] = item
    #         if 'type' not in submission_item['data']:
    #             submission_item['data']['type'] = (
    #                 'ManagedInstalls' if report_key == 'InstallResults' else 'ManagedUninstalls')
    #         # This UTC datetime gets converted to a naive datetime by
    #         # plistlib. Fortunately, we can just tell it that it's UTC.
    #         submission_item['date_managed'] = item['time'].replace(
    #             tzinfo=datetime.timezone.utc).isoformat()
    #         munki_submission['managed_items'][name] = submission_item

    # sal.set_checkin_results('Munki', munki_submission)


def get_profiles():
    try:
        temp_dir = pathlib.Path(tempfile.mkdtemp())
        profile_out = temp_dir / 'profiles.plist'

        cmd = ['/usr/bin/profiles', '-C', '-o', profile_out]
        # dev_null = open(os.devnull, 'w')
        try:
            subprocess.call(cmd, stdout=subprocess.PIPE)
        except OSError:
            return {}

        try:
            profiles = plistlib.loads(profile_out.read_bytes())
        except plistlib.InvalidFileException:
            return {}
    finally:
        profile_out.unlink(missing_ok=True)
        temp_dir.rmdir()
    return profiles

    # Drop all of the payload info we're not going to actual store.
    # for profile in profiles['_computerlevel']:
    #     cleansed_payloads = [_payload_cleanse(p) for p in profile.get('ProfileItems', [])]
    #     profile['ProfileItems'] = cleansed_payloads


def _payload_cleanse(payload):
    stored = ('PayloadIdentifier', 'PayloadUUID', 'PayloadType')
    return {k: payload[k] for k in stored}


if __name__ == "__main__":
    main()
