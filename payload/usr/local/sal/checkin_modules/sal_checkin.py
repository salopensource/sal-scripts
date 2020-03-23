#!/usr/local/sal/Python.framework/Versions/3.8/bin/python3


import sys

sys.path.insert(0, '/usr/local/sal')
import utils


__version__ = '1.0.0'


def main():
    _, _, bu_key = utils.get_server_prefs()
    sal_submission = {
        'extra_data': {
            'sal_version': utils.sal_version(),
            'key': bu_key,},
        'facts': {'checkin_module_version': __version__}}
    utils.set_checkin_results('Sal', sal_submission)


if __name__ == "__main__":
    main()
