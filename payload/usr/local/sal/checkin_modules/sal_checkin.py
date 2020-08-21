#!/usr/local/sal/Python.framework/Versions/Current/bin/python3


import sal


__version__ = '1.1.0'


def main():
    _, _, bu_key = sal.get_server_prefs()
    sal_submission = {
        'extra_data': {
            'sal_version': sal.__version__,
            'key': bu_key,},
        'facts': {'checkin_module_version': __version__}}
    sal.set_checkin_results('Sal', sal_submission)


if __name__ == "__main__":
    main()
