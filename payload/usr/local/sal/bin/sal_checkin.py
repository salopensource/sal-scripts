#!/usr/bin/python


import sys

sys.path.append('/usr/local/sal')
import utils


def main():
    _, _, bu_key = utils.get_server_prefs()
    sal_submission = {'key': bu_key, 'sal_version': utils.sal_version()}
    # TODO: CLean up; this is handled by a completely separate tool.
    # 'broken_client': bool

    utils.add_checkin_results('sal', sal_submission)


if __name__ == "__main__":
    main()
