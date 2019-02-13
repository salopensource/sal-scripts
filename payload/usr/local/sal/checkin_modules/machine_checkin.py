#!/usr/bin/python


import os
import subprocess
import sys

from SystemConfiguration import SCDynamicStoreCreate, SCDynamicStoreCopyValue

sys.path.append('/usr/local/munki')
from munkilib import munkicommon, FoundationPlist
sys.path.append('/usr/local/sal')
import macmodelshelf
import utils


MACHINE_KEYS = {
    'machine_model': {'old': 'MachineModel', 'new': 'machine_model'},
    'cpu_type': {'old': 'CPUType', 'new': 'cpu_type'},
    'cpu_speed': {'old': 'CurrentProcessorSpeed', 'new': 'current_processor_speed'},
    'memory': {'old': 'PhysicalMemory', 'new': 'physical_memory'}}
MEMORY_EXPONENTS = {'KB': 0, 'MB': 1, 'GB': 2, 'TB': 3}
__version__ = '1.0.0'


def main():
    machine_results = {'facts': {'checkin_module_version': __version__}}
    # Many machine properties have already been retrieved by Munki.
    # Use them.
    munki_report = get_managed_install_report()

    serial = munki_report['MachineInfo'].get('serial_number')
    if not serial:
        sys.exit('Unable to get MachineInfo from ManagedInstallReport.plist. This is usually due '
                 'to running Munki in Apple Software only mode.')
    machine_results['serial'] = serial
    machine_results['hostname'] = get_hostname()
    machine_results['console_user'] = munki_report['ConsoleUser']
    machine_results['os_family'] = 'Darwin'
    machine_results['operating_system'] = munki_report['MachineInfo']['os_vers']
    machine_results['hd_space'] = int(munki_report['AvailableDiskSpace'])
    machine_results['hd_total'] = get_disk_size()
    machine_results['hd_percent'] = str(
        machine_results['hd_space'] / float(machine_results['hd_total']))
    machine_results['machine_model'] = munki_report['MachineInfo']['machine_model']
    friendly_model = get_friendly_model(serial)
    if friendly_model:
        machine_results['machine_model_friendly'] = friendly_model

    system_profile = get_sys_profile()
    hwinfo = None
    for profile in system_profile:
        if profile['_dataType'] == 'SPHardwareDataType':
            hwinfo = profile['_items'][0]
            break

    if hwinfo:
        key_style = 'old' if 'MachineModel' in hwinfo else 'new'
        machine_results['cpu_type'] = hwinfo.get(MACHINE_KEYS['cpu_type'][key_style])
        machine_results['cpu_speed'] = hwinfo.get(MACHINE_KEYS['cpu_speed'][key_style])
        machine_results['memory'] = hwinfo.get(MACHINE_KEYS['memory'][key_style])
        machine_results['memory_kb'] = process_memory(machine_results['memory'])

    utils.set_checkin_results('machine', machine_results)


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
    except FoundationPlist.FoundationPlistException:
        munki_report = {}

    if 'MachineInfo' not in munki_report:
        munki_report['MachineInfo'] = {}

    return munki_report


def get_hostname():
    _, name_type, _ = utils.get_server_prefs()
    net_config = SCDynamicStoreCreate(None, "net", None, None)
    return get_machine_name(net_config, name_type)


def get_disk_size():
    """Returns total disk size in KBytes.

    Args:
      path: str, optional, default '/'

    Returns:
      int, KBytes in total disk space
    """
    try:
        stat = os.statvfs('/')
    except OSError:
        return 0
    total = (stat.f_blocks * stat.f_frsize) / 1024
    return int(total)


def get_friendly_model(serial):
    """Return friendly model name"""
    model_code = macmodelshelf.model_code(serial)
    model_name = macmodelshelf.model(model_code)
    return model_name


def process_memory(amount):
    """Convert the amount of memory like '4 GB' to the size in kb as int"""
    try:
        memkb = int(amount[:-3]) * \
            1024 ** MEMORY_EXPONENTS[amount[-2:]]
    except ValueError:
        memkb = int(float(amount[:-3])) * \
            1024 ** MEMORY_EXPONENTS[amount[-2:]]
    return memkb


def get_machine_name(net_config, nametype):
    """Return the ComputerName of this Mac."""
    sys_info = SCDynamicStoreCopyValue(net_config, "Setup:/System")
    if sys_info:
        return sys_info.get(nametype)
    return subprocess.check_output(['/usr/sbin/scutil', '--get', 'ComputerName'])


def get_sys_profile():
    """Get sysprofiler info.

    Returns:
        System Profiler report for networking and hardware as a plist
        dict, or an empty dict.
    """
    # Generate system profiler report for networking and hardware.
    system_profile = {}
    command = ['/usr/sbin/system_profiler', '-xml', 'SPNetworkDataType', 'SPHardwareDataType']
    try:
        stdout = subprocess.check_output(command)
    except subprocess.CalledProcessError:
        stdout = None

    if stdout:
        try:
            system_profile = FoundationPlist.readPlistFromString(stdout)
        except FoundationPlist.FoundationPlistException:
            pass

    return system_profile


if __name__ == "__main__":
    main()
