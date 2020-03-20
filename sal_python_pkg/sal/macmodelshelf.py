#!/usr/local/sal/Python.framework/Versions/3.8/bin/python3


import argparse
import dbm
import os
import re
import shelve
import subprocess
import sys
from xml.etree import ElementTree


DBPATH = "/usr/local/sal/macmodelshelf"


try:
    macmodelshelf = shelve.open(DBPATH)
except dbm.error as exception:
    exit(f"Couldn't open macmodelshelf.db: {exception}")


def model_code(serial):
    if "serial" in serial.lower(): # Workaround for machines with dummy serial numbers.
        return

    if 12 <= len(serial) <= 13:
        if serial.startswith("S"):
            # Remove S prefix from scanned codes.
            serial = serial[1:]
        return serial[8:]
    return


def lookup_mac_model_code_from_apple(model_code):
    tree = ElementTree.ElementTree()
    try:
        response = subprocess.check_output(
            ['curl', f"https://support-sp.apple.com/sp/product?cc={model_code}&lang=en_US"])
    except subprocess.CalledProcessError:
        pass
    try:
        tree = ElementTree.fromstring(response.decode())
    except ElementTree.ParseError:
        pass
    return tree.findtext("configCode")


CLEANUP_RES = [
    (re.compile(r"inch ? "), "inch, "),
    (re.compile(r"  "), " "),
]
def cleanup_model(model):
    for pattern, replacement in CLEANUP_RES:
        model = pattern.sub(replacement, model)
    return model


def model(code, cleanup=True):
    global macmodelshelf
    if code == None:
        return None
    code = code.upper()
    try:
        model = macmodelshelf[code]
    except KeyError:
        print(f"Looking up {code} from Apple", file=sys.stderr)
        model = lookup_mac_model_code_from_apple(code)
        if model:
            macmodelshelf[code] = model
    if cleanup and model:
        return cleanup_model(model)
    else:
        return model


def _dump(cleanup=True, format=u"json"):
    assert format in (u"python", u"json", u"markdown")
    def clean(model):
        if cleanup:
            return cleanup_model(model)
        else:
            return model
    items = macmodelshelf.keys()
    items.sort()
    items.sort(key=len)
    if format == "python":
        print("macmodelshelfdump = {")
        print(",\n".join([f'    "{code}": "{clean(macmodelshelf[code])}"' for code in items]))
        print("}")
    elif format == "json":
        print("{")
        print(",\n".join([f'    "{code}": "{clean(macmodelshelf[code])}"' for code in items]))
        print("}")
    elif format == "markdown":
        print("Code | Model")
        print(":--- | :---")
        print("\n".join('`{code}` | {clean(macmodelshelf[code])}' for code in items))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n", "--no-cleanup", action="store_false", dest="cleanup",
        help="Don't clean up model strings.")
    parser.add_argument("code", help="Serial number or model code")
    args = parser.parse_args()

    dump_format = {
        "dump": "python",
        "dump-python": "python",
        "dump-json": "json",
        "dump-markdown": "markdown",
    }
    if args.code in dump_format:
        _dump(args.cleanup, dump_format[args.code])
        exit()

    if 11 <= len(args.code) <= 13:
        result = model(model_code(args.code), cleanup=args.cleanup)
    else:
        result = model(args.code, cleanup=args.cleanup)
    if result:
        print(result)
        exit()
    else:
        print(f"Unknown model {args.code}", file=sys.stderr)
        exit(os.EX_UNAVAILABLE)


if __name__ == '__main__':
    main()
