#!/usr/bin/python
"""sal-submit

Coordinates running checkin modules and submitting their results to Sal.
"""


import os
import optparse
import sys

sys.path.append('/usr/local/munki')
from munkilib import FoundationPlist, munkicommon


BUNDLE_ID = 'com.github.salopensource.sal'
VERSION = '2.1.3'


def main():
    set_verbosity()
    exit_if_not_root()
    if utils.python_script_running('sal-submit')
        sys.exit('Another instance of sal-submit is already running. Exiting.')

    time.sleep(1)
    if  utils.python_script_running('managedsoftwareupdate')
        sys.exit('managedsoftwareupdate is running. Exiting.')
    # report = get_managed_install_report()
    # serial = report['MachineInfo'].get('serial_number')
    # if not serial:
    #     sys.exit('Unable to get MachineInfo from ManagedInstallReport.plist. '
    #              'This is usually due to running Munki in Apple Software only '
    #              'mode.')
    # runtype = get_runtype(report)
    # report['MachineInfo']['SystemProfile'] = get_sys_profile()
    # friendly_model = get_friendly_model(serial)
    # if friendly_model:
    #     report['MachineInfo']['machine_model_friendly'] = friendly_model
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

    # ServerURL, NameType, bu_key = get_server_prefs()
    # net_config = SCDynamicStoreCreate(None, "net", None, None)
    # name = get_machine_name(net_config, NameType)
    # run_uuid = uuid.uuid4()
    # submission = get_data(serial, bu_key, name, run_uuid)

    # # Shallow copy the submission dict to reuse common values and avoid
    # # wasting bandwidth by sending unrelated data. (Alternately, we
    # # could `del submission[some_key]`).
    # send_checkin(ServerURL, copy.copy(submission), report)
    # # Only perform these when a user isn't running MSC manually to speed up the
    # # run
    # if runtype != 'manual':
    #     send_hashed(ServerURL, copy.copy(submission))
    #     send_install(ServerURL, copy.copy(submission))
    #     send_catalogs(ServerURL, copy.copy(submission))
    #     send_profiles(ServerURL, copy.copy(submission))

    # touchfile = '/Users/Shared/.com.salopensource.sal.run'
    # if os.path.exists(touchfile):
    #     os.remove(touchfile)


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


if __name__ == "__main__":
    main()
