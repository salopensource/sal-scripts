#!/usr/bin/python


import sys

sys.path.append('/usr/local/sal')
import utils


__version__ = '1.0.0'


def main():
    _, _, bu_key = utils.get_server_prefs()
    sal_submission = {
        'key': bu_key, 'sal_version': utils.sal_version(),
        'facts': {'checkin_module_version': __version__}}
    utils.set_checkin_results('sal', sal_submission)


if __name__ == "__main__":
    main()
