#!/usr/local/sal/Python.framework/Versions/Current/bin/python3


import pathlib
import plistlib
import subprocess
import tempfile

import sal


__version__ = "1.0.0"


def main():
    profiles = get_profiles()
    submission = {}
    submission["facts"] = {"checkin_module_version": __version__}
    submission["managed_items"] = {}
    for profile in profiles.get("_computerlevel", []):
        name = profile["ProfileDisplayName"]
        submission_item = {}
        submission_item["name"] = name
        submission_item["date_managed"] = profile["ProfileInstallDate"]
        submission_item["status"] = "PRESENT"

        data = {}
        payloads = profile.get("ProfileItems", [])
        for count, payload in enumerate(payloads, start=1):
            data[f"payload {count}"] = payload

        data["payload_types"] = ", ".join(p["PayloadType"] for p in payloads)
        data["profile_description"] = profile.get("ProfileDescription", "None")
        data["identifier"] = profile["ProfileIdentifier"]
        data["organization"] = profile.get("ProfileOrganization" or "None")
        data["uuid"] = profile["ProfileUUID"]
        data["verification_state"] = profile.get("ProfileVerificationState", "")
        submission_item["data"] = data

        submission["managed_items"][name] = submission_item

    sal.set_checkin_results("Profiles", submission)


def get_profiles():
    try:
        temp_dir = pathlib.Path(tempfile.mkdtemp())
        profile_out = temp_dir / "profiles.plist"

        cmd = ["/usr/bin/profiles", "-C", "-o", profile_out]
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


if __name__ == "__main__":
    main()
