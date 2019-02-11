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

    server_url, name_type, bu_key = utils.get_server_prefs()
    send_checkin(server_url)

    # plugin_results_path = '/usr/local/sal/plugin_results.plist'
    # try:
    #     run_external_scripts(runtype)
    #     report['Plugin_Results'] = get_plugin_results(plugin_results_path)
    # finally:
    #     if os.path.exists(plugin_results_path):
    #         os.remove(plugin_results_path)

    # Shallow copy the submission dict to reuse common values and avoid
    # wasting bandwidth by sending unrelated data. (Alternately, we
    # could `del submission[some_key]`).
    # TODO: This isn't right at all. Just left uncommented.
    # send_checkin(server_url, copy.copy(submission), report)
    # Only perform these when a user isn't running MSC manually to speed up the
    # run
    # TODO: These need to be updated for the new submission format
    # if runtype != 'manual':
    #     send_hashed(server_url, copy.copy(submission))
    #     send_install(server_url, copy.copy(submission))
    #     send_catalogs(server_url, copy.copy(submission))
    #     send_profiles(server_url, copy.copy(submission))

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
    send_report(checkinurl)


def send_report(url):
    stdout, stderr = utils.curl(url, json_path=utils.RESULTS_PATH)
    if stderr:
        munkicommon.display_debug2(stderr)
    stdout_list = stdout.split("\n")
    if "<h1>Page not found</h1>" not in stdout_list:
        munkicommon.display_debug2(stdout)
    return stdout, stderr


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
if __name__ == "__main__":
    main()
