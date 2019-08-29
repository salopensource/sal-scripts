#!/usr/bin/python


import datetime
import os
import plistlib
import re
import subprocess
import sys
import xml.parsers.expat
from distutils.version import StrictVersion

sys.path.insert(0, '/usr/local/sal')
import utils


__version__ = '1.0.1'


def main():
    sus_submission = {}
    sus_submission['facts'] = get_sus_facts()

    # Process managed items and update histories.
    sus_submission['managed_items'] = get_sus_install_report()
    sus_submission['update_history'] = []

    pending = get_pending()
    sus_submission['managed_items'].update(pending)

    utils.set_checkin_results('Apple Software Update', sus_submission)


def get_sus_install_report():
    """Return installed apple updates from softwareupdate"""
    try:
        history = plistlib.readPlist('/Library/Receipts/InstallHistory.plist')
        # TODO: Put in the correct exceptions
    except (IOError, xml.parsers.expat.ExpatError):
        history = []
    return {
        i['displayName']: {
            'date_managed': i['date'],
            'status': 'PRESENT',
            'data': {
                'type': 'Apple SUS Install',
                'version': i['displayVersion'].strip()
            }
        } for i in history if i['processName'] == 'softwareupdated'}


def get_sus_facts():
    result = {'checkin_module_version': __version__}
    before_dump = datetime.datetime.utcnow()
    cmd = ['softwareupdate', '--dump-state']
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        return result

    with open('/var/log/install.log') as handle:
        install_log = handle.readlines()

    for line in reversed(install_log):
        # TODO: Stop if we go before the subprocess call datetime-wise
        if 'Catalog: http' in line and 'catalog' not in result:
            result['catalog'] = line.split()[-1]
        elif 'SUScan: Elapsed scan time = ' in line and 'last_check' not in result:
            # Example date 2019-02-08 10:49:56-05
            # Ahhhh, python 2 stdlib... Doesn't support the %z UTC
            # offset correctly.

            # So split off UTC offset.
            raw_date = ' '.join(line.split()[:2])
            # and make a naive datetime from it.
            naive = datetime.datetime.strptime(raw_date[:-3], '%Y-%m-%d %H:%M:%S')
            # Convert the offset in hours to an int, including the sign.
            offset = int(raw_date[-3:])
            # Invert the offset by subtracting from the naive datetime.
            last_check_datetime = naive - datetime.timedelta(hours=offset)
            # Finally, convert to ISO format and tack a Z on to show
            # we're using UTC time now.
            result['last_check'] = last_check_datetime.isoformat() + 'Z'

        log_time = _get_log_time(line)
        if log_time and before_dump < log_time:
            # Let's not look earlier than when we started
            # softwareupdate.
            break

        elif 'catalog' in result and 'last_check' in result:
            # Once we have both facts, bail; no need to process the
            # entire file.
            break

    return result


def _get_log_time(line):
    try:
        result = datetime.datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None
    utc_result = result - datetime.timedelta(hours=int(line[19:22]))
    return utc_result


def get_pending():
    pending_items = {}
    cmd = ['softwareupdate', '-l', '--no-scan']
    try:
        # softwareupdate outputs "No new software available" to stderr,
        # so we pipe it off.
        output = subprocess.check_output(cmd, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        return pending_items

    # Example output

    # Software Update Tool

    # Software Update found the following new or updated software:
    # * macOS High Sierra 10.13.6 Update-
    #       macOS High Sierra 10.13.6 Update ( ), 1931648K [recommended] [restart]
    # * iTunesX-12.8.2
    #       iTunes (12.8.2), 273564K [recommended]

    for line in output.splitlines():
        if line.strip().startswith('*'):
            item = {'date_managed': datetime.datetime.utcnow().isoformat() + 'Z'}
            item['status'] = 'PENDING'
            pending_items[line.strip()[2:]] = item

    # TODO: Catalina

    return pending_items





if __name__ == "__main__":
    main()
