#!/usr/bin/python
"""sal-submit

Coordinates running checkin modules and submitting their results to Sal.
"""


import json
import os
import optparse
import subprocess
import sys

from SystemConfiguration import SCDynamicStoreCreate, SCDynamicStoreCopyValue

sys.path.append('/usr/local/munki')
from munkilib import FoundationPlist, munkicommon
sys.path.append('/usr/local/sal')
import utils


BUNDLE_ID = 'com.github.salopensource.sal'
CHECKIN_MODULES_DIR = '/usr/local/sal/checkin_modules'
VERSION = '2.1.3'


def main():
    set_verbosity()
    exit_if_not_root()
    if utils.python_script_running('sal-submit')
        sys.exit('Another instance of sal-submit is already running. Exiting.')

    time.sleep(1)
    if  utils.python_script_running('managedsoftwareupdate')
        sys.exit('managedsoftwareupdate is running. Exiting.')

    submission = {}

    utils.run_scripts(CHECKIN_MODULES_DIR, sys.argv[1])

    # TODO: Build Munki section
    # TODO: Build Sal section

    # puppet_version = puppet_vers()
    # if puppet_version != "" and puppet_version is not None:
    #     report['Puppet_Version'] = puppet_version
    # puppet_report = get_puppet_report()
    # if puppet_report != {}:
    #     report['Puppet'] = puppet_report

    # plugin_results_path = '/usr/local/sal/plugin_results.plist'
    # try:
    #     run_external_scripts(runtype)
    #     report['Plugin_Results'] = get_plugin_results(plugin_results_path)
    # finally:
    #     if os.path.exists(plugin_results_path):
    #         os.remove(plugin_results_path)

    # insert_name = False
    # report['Facter'] = get_facter_report()

    # if report['Facter']:
    #     insert_name = True

    # if utils.pref('GetGrains'):
    #     grains = get_grain_report(insert_name)
    #     report['Facter'].update(grains)
    #     insert_name = True  # set in case ohai is needed as well
    # if utils.pref('GetOhai'):
    #     if utils.pref('OhaiClientConfigPath'):
    #         clientrbpath = utils.pref('OhaiClientConfigPath')
    #     else:
    #         clientrbpath = '/private/etc/chef/client.rb'
    #     ohais = get_ohai_report(insert_name, clientrbpath)
    #     report['Facter'].update(ohais)

    # report['os_family'] = 'Darwin'

    server_url, name_type, bu_key = utils.get_server_prefs()
    # TODO: Move to machine module
    # net_config = SCDynamicStoreCreate(None, "net", None, None)
    # name = get_machine_name(net_config, name_type)
    # run_uuid = uuid.uuid4()
    # submission = get_data(serial, bu_key, name, run_uuid)

    # Shallow copy the submission dict to reuse common values and avoid
    # wasting bandwidth by sending unrelated data. (Alternately, we
    # could `del submission[some_key]`).
    # TODO: This isn't right at all. Just left uncommented.
    send_checkin(server_url, copy.copy(submission), report)
    # Only perform these when a user isn't running MSC manually to speed up the
    # run
    # TODO: These need to be updated for the new submission format
    if runtype != 'manual':
        send_hashed(server_url, copy.copy(submission))
        send_install(server_url, copy.copy(submission))
        send_catalogs(server_url, copy.copy(submission))
        send_profiles(server_url, copy.copy(submission))

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


def send_checkin(server_url, checkin_data, report):
    checkinurl = os.path.join(server_url, 'checkin', '')
    munkicommon.display_debug2("Checkin Response:")
    send_report(checkinurl, checkin_data)


def send_report(url, report):
    encoded_data = urllib.urlencode(report)
    stdout, stderr = utils.curl(url, encoded_data)
    if stderr:
        munkicommon.display_debug2(stderr)
    stdout_list = stdout.split("\n")
    if "<h1>Page not found</h1>" not in stdout_list:
        munkicommon.display_debug2(stdout)
    return stdout, stderr


if __name__ == "__main__":
    main()
