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


if __name__ == "__main__":
    main()
