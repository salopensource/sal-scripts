import logging
import os

from sal.client import get_sal_client, MacKeychainClient
from sal.utils import pref


def setup_sal_client():
    ca_cert = pref('CACert', '')
    cert = pref('SSLClientCertificate', '')
    key = pref('SSLClientKey', '')
    exists = map(os.path.exists, (ca_cert, cert, key))
    if any(exists):
        if not all(exists):
            logging.warning(
                'Argument warning! If using the `CACert`, `SSLClientCertificate`, or '
                '`SSLClientKey` prefs, they must all be either paths to cert files or the '
                'common name of the certs to find in the keychain.')

        # If any of the above have been passed as a path, we have to
        # use a vanilla Session.
        logging.debug('Using SalClient')
        client = get_sal_client()
    else:
        # Assume that any passed certs are by CN since they don't
        # exist as files anywhere.
        # If we're going to use the keychain, we need to use a
        # macsesh
        logging.debug('Using MacKeychainClient')
        client = get_sal_client(MacKeychainClient)

    if ca_cert:
        client.verify = ca_cert
    if cert:
        client.cert = (cert, key) if key else cert

    basic_auth = pref('BasicAuth')
    if basic_auth:
        key = pref('key', '')
        client.auth = ('sal', key)

    client.base_url = pref('ServerURL')


