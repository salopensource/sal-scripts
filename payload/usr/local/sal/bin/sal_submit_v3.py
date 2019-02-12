#!/usr/bin/python
"""sal-submit

Coordinates running checkin modules and submitting their results to Sal.
"""


import json
import os
import optparse
import stat
import subprocess
import sys
import tempfile
import time

from SystemConfiguration import SCDynamicStoreCreate, SCDynamicStoreCopyValue

sys.path.append('/usr/local/munki')
from munkilib import FoundationPlist, munkicommon
sys.path.append('/usr/local/sal')
import utils


CHECKIN_MODULES_DIR = '/usr/local/sal/checkin_modules'


def main():
    set_verbosity()
    exit_if_not_root()
    if utils.python_script_running('sal-submit'):
        sys.exit('Another instance of sal-submit is already running. Exiting.')

    time.sleep(1)
    if utils.python_script_running('managedsoftwareupdate'):
        sys.exit('managedsoftwareupdate is running. Exiting.')

    utils.run_checkin_modules(CHECKIN_MODULES_DIR)

    submission = utils.get_checkin_results()
    runtype = get_runtype(submission)

    plugin_results_path = '/usr/local/sal/plugin_results.plist'
    # TODO: Clean up error handling.
    try:
        run_external_scripts(runtype)
        plugin_results = get_plugin_results(plugin_results_path)
    finally:
        if os.path.exists(plugin_results_path):
            os.remove(plugin_results_path)
    utils.set_checkin_results('plugin_results', plugin_results)

    server_url, _, machine_group_key = utils.get_server_prefs()
    send_checkin(server_url)

    # Speed up manual runs by skipping these potentially slow-running,
    # and infrequently changing tasks.
    if runtype != 'manual':
        send_inventory(server_url, submission['machine']['serial'])
        send_catalogs(server_url, machine_group_key)
        send_profiles(server_url, submission['machine']['serial'])

    touchfile = '/Users/Shared/.com.salopensource.sal.run'
    if os.path.exists(touchfile):
        os.remove(touchfile)


def set_verbosity():
    """Set the verbosity based on options or munki verbosity level."""
    opts = get_options()
    munkicommon.verbose = (5 if opts.debug else int(os.environ.get('MUNKI_VERBOSITY_LEVEL', 0)))


def get_options():
    """Return commandline options."""
    usage = "%prog [options]"
    option_parser = optparse.OptionParser(usage=usage)
    option_parser.add_option(
        "-d", "--debug", default=False, action="store_true", help="Enable debug output.")
    # We have no arguments, so don't store the results.
    opts, _ = option_parser.parse_args()
    return opts


def exit_if_not_root():
    """Exit if the executing user is not root."""
    uid = os.geteuid()
    if uid != 0:
        sys.exit("Manually running this script requires sudo.")


def send_checkin(server_url):
    checkinurl = os.path.join(server_url, 'checkin', '')
    munkicommon.display_debug2("Checkin Response:")
    utils.send_report(checkinurl, json_path=utils.RESULTS_PATH)


def run_external_scripts(runtype):
    external_scripts_dir = '/usr/local/sal/external_scripts'

    if os.path.exists(external_scripts_dir):
        for root, dirs, files in os.walk(external_scripts_dir, topdown=False):
            for script in files:
                script_path = os.path.join(root, script)

                script_stat = os.stat(script_path)
                executable = script_stat.st_mode & stat.S_IXUSR
                if executable:
                    try:
                        subprocess.call(
                            [script_path, runtype], stdin=None)
                    except OSError:
                        munkicommon.display_debug2(
                            "Couldn't run {}".format(script_path))
                else:
                    msg = "'{}' is not executable! Skipping."
                    munkicommon.display_debug1(msg.format(script_path))


def get_runtype(submission):
    munki = submission.get('munki', {})
    return munki['runtype']


def get_plugin_results(plugin_results_plist):
    """ Read external data plist if it exists and return a dict."""
    result = []
    if os.path.exists(plugin_results_plist):
        try:
            plist_data = FoundationPlist.readPlist(plugin_results_plist)
        except FoundationPlistException:
            munkicommon.display_debug2('Could not read external data plist.')
            return result
        munkicommon.display_debug2('External data plist:')

        results = utils.unobjctify(plist_data)

        # TODO: This will fail without a serializer
        # munkicommon.display_debug2(json.dumps(result, indent=4))
    else:
        munkicommon.display_debug2('No external data plist found.')

    return result


# TODO: REFACTOR!
def send_inventory(server_url, serial):
    hash_url = os.path.join(server_url, 'inventory/hash', serial, '')
    inventory_submit_url = os.path.join(server_url, 'inventory/submit', '')

    managed_install_dir = munkicommon.pref('ManagedInstallDir')
    inventory_plist = os.path.join(managed_install_dir, 'ApplicationInventory.plist')
    munkicommon.display_debug2('ApplicationInventory.plist Path: {}'.format(inventory_plist))

    inventory, inventory_hash = utils.get_file_and_hash(inventory_plist)
    if inventory:
        serverhash = None
        serverhash, stderr = utils.curl(hash_url)
        if stderr:
            return
        if serverhash != inventory_hash:
            inventory_submission = {
                'serial': serial,
                'base64bz2inventory': utils.submission_encode(inventory)}
            munkicommon.display_debug2("Hashed Report Response:")
            utils.send_report(inventory_submit_url, form_data=inventory_submission)


def send_catalogs(server_url, machine_group_key):
    hash_url = os.path.join(server_url, 'catalog/hash', '')
    catalog_submit_url = os.path.join(server_url, 'catalog/submit', '')
    managed_install_dir = munkicommon.pref('ManagedInstallDir')
    catalog_dir = os.path.join(managed_install_dir, 'catalogs')

    check_list = []
    if os.path.exists(catalog_dir):
        for file in os.listdir(catalog_dir):
            # don't operate on hidden files (.DS_Store etc)
            if not file.startswith('.'):
                _, catalog_hash = utils.get_file_and_hash(file)
                check_list.append({'name': file, 'sha256hash': catalog_hash})

        catalog_check_plist = FoundationPlist.writePlistToString(check_list)

    hash_submission = {
        'key': machine_group_key,
        'catalogs': utils.submission_encode(catalog_check_plist)}
    response, stderr = utils.send_report(hash_url, form_data=hash_submission)

    if stderr is not None:
        try:
            remote_data = FoundationPlist.readPlistFromString(response)
        except FoundationPlist.NSPropertyListSerializationException:
            remote_data = {}

        for catalog in check_list:
            if catalog not in remote_data:
                contents, _ = utils.get_file_and_hash(os.path.join(catalog_dir, catalog['name']))
                catalog_submission = {
                    'key': machine_group_key,
                    'base64bz2catalog': utils.submission_encode(contents),
                    'name': catalog['name'],
                    'sha256hash': catalog['sha256hash']}

                munkicommon.display_debug2(
                    "Submitting Catalog: {}".format(catalog['name']))
                try:
                    utils.send_report(catalog_submit_url, form_data=catalog_submission)
                except OSError:
                    munkicommon.display_debug2(
                        "Error while submitting Catalog: {}".format(catalog['name']))


def send_profiles(server_url, serial):
    profile_submit_url = os.path.join(server_url, 'profiles/submit', '')

    temp_dir = tempfile.mkdtemp()
    profile_out = os.path.join(temp_dir, 'profiles.plist')

    cmd = ['/usr/bin/profiles', '-C', '-o', profile_out]
    dev_null = open(os.devnull, 'w')
    try:
        subprocess.call(cmd, stdout=dev_null)
    except OSError:
        munkicommon.display_debug2("Couldn't output profiles.")
        return

    profiles, _ = utils.get_file_and_hash(profile_out)

    os.remove(profile_out)

    profile_submission = {
        'serial': serial,
        'base64bz2profiles': utils.submission_encode(profiles)}

    munkicommon.display_debug2("Profiles Response:")
    stdout, stderr = utils.send_report(profile_submit_url, form_data=profile_submission)


if __name__ == "__main__":
    main()
