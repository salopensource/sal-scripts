#!/usr/bin/python


import subprocess
import sys

from SystemConfiguration import (
    SCDynamicStoreCreate, SCDynamicStoreCopyValue, SCDynamicStoreCopyConsoleUser)

sys.path.insert(0, '/usr/local/munki')
from munkilib import FoundationPlist
sys.path.insert(0, '/usr/local/sal')
import macmodelshelf
import utils


MEMORY_EXPONENTS = {'KB': 0, 'MB': 1, 'GB': 2, 'TB': 3}
__version__ = '1.0.0'


def main():
    machine_results = {'facts': {'checkin_module_version': __version__}}
    extras = {}
    extras['hostname'] = get_hostname()
    extras['os_family'] = 'Darwin'
    extras['console_user'] = get_console_user()[0]
    extras.update(process_system_profile())
    machine_results['extra_data'] = extras
    utils.set_checkin_results('Machine', machine_results)


def process_system_profile():
    machine_results = {}
    system_profile = get_sys_profile()

    if not system_profile:
        # We can't continue if system_profiler dies.
        return machine_results

    machine_results['serial'] = system_profile['SPHardwareDataType'][0]['serial_number']
    os_version = system_profile['SPSoftwareDataType'][0]['os_version'].split()[1]
    if os_version == 'X':
        os_version = system_profile['SPSoftwareDataType'][0]['os_version'].split()[2]
    machine_results['operating_system'] = os_version
    machine_results['machine_model'] = system_profile['SPHardwareDataType'][0]['machine_model']
    friendly_model = get_friendly_model(machine_results['serial'])
    if friendly_model:
        machine_results['machine_model_friendly'] = friendly_model
    machine_results['cpu_type'] = system_profile['SPHardwareDataType'][0].get('cpu_type', '')
    machine_results['cpu_speed'] = (
        system_profile['SPHardwareDataType'][0]['current_processor_speed'])
    machine_results['memory'] = system_profile['SPHardwareDataType'][0]['physical_memory']
    machine_results['memory_kb'] = process_memory(machine_results['memory'])

    for device in system_profile['SPStorageDataType']:
        if device['mount_point'] == '/':
            # div by 1000.0 to
            # a) Convert to Apple base 10 kilobytes
            # b) Cast to python floats
            machine_results['hd_space'] = device['free_space_in_bytes']
            machine_results['hd_total'] = device['size_in_bytes']
            # We want the % used, not of free space, so invert.
            machine_results['hd_percent'] = '{:.2f}'.format(
                abs(float(machine_results['hd_space']) / machine_results['hd_total'] - 1) * 100)

    return machine_results


def get_hostname():
    _, name_type, _ = utils.get_server_prefs()
    net_config = SCDynamicStoreCreate(None, "net", None, None)
    return get_machine_name(net_config, name_type)


def get_machine_name(net_config, nametype):
    """Return the ComputerName of this Mac."""
    sys_info = SCDynamicStoreCopyValue(net_config, "Setup:/System")
    if sys_info:
        return sys_info.get(nametype)
    return subprocess.check_output(['/usr/sbin/scutil', '--get', 'ComputerName'])


def get_friendly_model(serial):
    """Return friendly model name"""
    model_code = macmodelshelf.model_code(serial)
    model_name = macmodelshelf.model(model_code)
    return model_name


def process_memory(amount):
    """Convert the amount of memory like '4 GB' to the size in kb as int"""
    try:
        memkb = int(amount[:-3]) * 1024 ** MEMORY_EXPONENTS[amount[-2:]]
    except ValueError:
        memkb = int(float(amount[:-3])) * 1024 ** MEMORY_EXPONENTS[amount[-2:]]
    return memkb


def get_sys_profile():
    """Get sysprofiler info.

    Returns:
        System Profiler report for networking, drives, and hardware as a
        plist dict, or an empty dict.
    """
    command = [
        '/usr/sbin/system_profiler', '-xml', 'SPHardwareDataType', 'SPStorageDataType',
        'SPSoftwareDataType']
    try:
        output = subprocess.check_output(command)
    except subprocess.CalledProcessError:
        return {}

    try:
        system_profile = FoundationPlist.readPlistFromString(output)
    except FoundationPlist.FoundationPlistException:
        system_profile = {}

    # sytem_profiler gives us back an array; convert to a dict with just
    # the data we care about.
    results = {}
    for data_type in system_profile:
        key = data_type['_dataType']
        results[key] = data_type['_items']

    return results


def get_console_user():
    """Get informatino about the console user

    Returns:
        3-Tuple of (str) username, (int) uid, (int) gid
    """
    return SCDynamicStoreCopyConsoleUser(None, None, None)


if __name__ == "__main__":
    main()
