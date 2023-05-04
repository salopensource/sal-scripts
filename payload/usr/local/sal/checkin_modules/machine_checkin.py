#!/usr/local/sal/Python.framework/Versions/Current/bin/python3


import pathlib
import plistlib
import re
import subprocess
import sys
from xml.etree import ElementTree

import macsesh
from SystemConfiguration import (
    SCDynamicStoreCreate,
    SCDynamicStoreCopyValue,
    SCDynamicStoreCopyConsoleUser,
)

import sal


MODEL_PATH = pathlib.Path("/usr/local/sal/model_cache")
MEMORY_EXPONENTS = {"KB": 0, "MB": 1, "GB": 2, "TB": 3}
__version__ = "1.1.0"


def main():
    machine_results = {"facts": {"checkin_module_version": __version__}}
    extras = {}
    extras["hostname"] = get_hostname()
    extras["os_family"] = "Darwin"
    extras["console_user"] = get_console_user()[0]
    extras.update(process_system_profile())
    machine_results["extra_data"] = extras
    sal.set_checkin_results("Machine", machine_results)


def process_system_profile():
    machine_results = {}
    system_profile = get_sys_profile()

    if not system_profile:
        # We can't continue if system_profiler dies.
        return machine_results

    machine_results["serial"] = system_profile["SPHardwareDataType"][0].get(
        "serial_number"
    )
    os_version = system_profile["SPSoftwareDataType"][0].get("os_version").split()[1]
    if os_version == "X":
        os_version = (
            system_profile["SPSoftwareDataType"][0].get("os_version").split()[2]
        )

    machine_results["operating_system"] = os_version
    machine_results["machine_model"] = system_profile["SPHardwareDataType"][0].get(
        "machine_model"
    )

    if rsr_supported(os_version):
        rsr_version = get_rsr_version()
        machine_results["rsr_version"] = rsr_version
        if rsr_version != "":
            machine_results["operating_system"] = os_version + " " + rsr_version

    udid = system_profile["SPHardwareDataType"][0].get("provisioning_UDID")
    if udid is None:
        # plaform_UUID was the unique id until macOS 10.15
        udid = system_profile["SPHardwareDataType"][0].get("platform_UUID")
    friendly_model = get_friendly_model(serial=machine_results["serial"], udid=udid)
    if friendly_model:
        machine_results["machine_model_friendly"] = friendly_model
    if system_profile["SPHardwareDataType"][0].get("chip_type", None):
        machine_results["cpu_type"] = system_profile["SPHardwareDataType"][0].get(
            "chip_type", ""
        )
    else:
        machine_results["cpu_type"] = system_profile["SPHardwareDataType"][0].get(
            "cpu_type", ""
        )
    machine_results["cpu_speed"] = system_profile["SPHardwareDataType"][0].get(
        "current_processor_speed", ""
    )
    machine_results["memory"] = system_profile["SPHardwareDataType"][0].get(
        "physical_memory", ""
    )
    machine_results["memory_kb"] = process_memory(machine_results["memory"])

    for device in system_profile["SPStorageDataType"]:
        if device["mount_point"] == "/":
            # div by 1000.0 to
            # a) Convert to Apple base 10 kilobytes
            # b) Cast to python floats
            machine_results["hd_space"] = device["free_space_in_bytes"]
            machine_results["hd_total"] = device["size_in_bytes"]
            # We want the % used, not of free space, so invert.
            machine_results["hd_percent"] = "{:.2f}".format(
                abs(
                    float(machine_results["hd_space"]) / machine_results["hd_total"] - 1
                )
                * 100
            )

    return machine_results


def rsr_supported(os_version):
    major_os = os_version.split(".")[0]
    if int(major_os) >= 13:
        return True
    return False


def get_rsr_version():
    try:
        return subprocess.check_output(
            ["/usr/bin/sw_vers", "--ProductVersionExtra"], text=True
        ).strip()
    except:
        return ""


def get_hostname():
    name_type = sal.sal_pref("NameType", default="ComputerName")
    net_config = SCDynamicStoreCreate(None, "net", None, None)
    return get_machine_name(net_config, name_type)


def get_machine_name(net_config, nametype):
    """Return the ComputerName of this Mac."""
    sys_info = SCDynamicStoreCopyValue(net_config, "Setup:/System")
    if sys_info:
        return sys_info.get(nametype)
    return subprocess.check_output(
        ["/usr/sbin/scutil", "--get", "ComputerName"], text=True
    ).strip()


def get_friendly_model(serial, udid):
    """Return friendly model name"""
    cmd = ["/usr/sbin/ioreg", "-arc", "IOPlatformDevice", "-k", "product-name"]
    try:
        out = subprocess.check_output(cmd)
    except:
        pass
    if out:
        try:
            data = plistlib.loads(out)
            if len(data) != 0:
                return (
                    data[0]
                    .get("product-name")
                    .decode("ascii", "ignore")
                    .strip()
                    .strip("\x00")
                    .strip()
                )
        except:
            pass

    # set up cache file for this udid...create dir,
    MODEL_PATH.mkdir(mode=0o755, parents=True, exist_ok=True)

    # name cache for this udid
    UDID_CACHE_PATH = pathlib.Path(MODEL_PATH, "%s.txt" % (udid))
    for cache_file in MODEL_PATH.iterdir():
        # clean up any other files in dir
        if cache_file != UDID_CACHE_PATH:
            try:
                cache_file.unlink()
            except:
                pass

    if not UDID_CACHE_PATH.exists():
        model = cleanup_model(query_apple_support(serial))
        if model:
            UDID_CACHE_PATH.write_text(model)
    else:
        try:
            model = UDID_CACHE_PATH.read_text().strip()
        except:
            model = None

    return model


def get_model_code(serial):
    # Workaround for machines with dummy serial numbers.
    if "serial" in serial.lower():
        return

    if 12 <= len(serial) <= 13:
        if serial.startswith("S"):
            # Remove S prefix from scanned codes.
            serial = serial[1:]
        return serial[8:].upper()

    elif 11 <= len(serial) <= 12:
        # 2010 Mac Pros starting with H or Y are 11 characters
        return serial[8:].upper()

    return


def query_apple_support(serial):
    model_code = get_model_code(serial)
    tree = ElementTree.ElementTree()
    session = macsesh.Session()
    response = session.get(
        f"https://support-sp.apple.com/sp/product?cc={model_code}&lang=en_US"
    )
    try:
        tree = ElementTree.fromstring(response.text)
    except ElementTree.ParseError:
        tree = None
    return tree.findtext("configCode") if tree else None


def cleanup_model(model):
    cleanup_res = [(re.compile(r"inch ? "), "inch, "), (re.compile(r"  "), " ")]
    if model:
        for pattern, replacement in cleanup_res:
            model = pattern.sub(replacement, model)
    return model


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
        "/usr/sbin/system_profiler",
        "-xml",
        "SPHardwareDataType",
        "SPStorageDataType",
        "SPSoftwareDataType",
    ]
    try:
        output = subprocess.check_output(command)
    except subprocess.CalledProcessError:
        return {}

    try:
        system_profile = plistlib.loads(output)
    except plistlib.InvalidException:
        system_profile = {}

    # sytem_profiler gives us back an array; convert to a dict with just
    # the data we care about.
    results = {}
    for data_type in system_profile:
        key = data_type["_dataType"]
        results[key] = data_type["_items"]

    return results


def get_console_user():
    """Get informatino about the console user

    Returns:
        3-Tuple of (str) username, (int) uid, (int) gid
    """
    return SCDynamicStoreCopyConsoleUser(None, None, None)


if __name__ == "__main__":
    main()
