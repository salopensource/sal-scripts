import logging

import macsesh

from sal.utils import pref


_client_instance = None


class SalClient():

    basic_timeout = (3.05, 4)
    post_timeout = (3.05, 8)
    base_url = ''

    def __init__(self):
        self.sesh = macsesh.KeychainSession()
        # sesh = macsesh.SecureTransportSession()

        base_url = pref('ServerURL')
        self.base_url = base_url if not base_url.endswith('/') else base_url[:-1]

        ca_cert = pref('CACert')
        if ca_cert:
            self.sesh.verify = ca_cert

        basic_auth = pref('BasicAuth')
        if basic_auth:
            key = pref('key', '')
            self.sesh.auth = ('sal', key)

        # TODO: Handle keychain-based certs.
        cert = pref('SSLClientCertificate')
        key = pref('SSLClientKey')
        if cert:
            self.sesh.cert = (cert, key) if key else cert

    @property
    def auth(self):
        return self.sesh.auth

    @auth.setter
    def auth(self, creds):
        self.sesh.auth = creds

    def get(self, url):
        url = self.build_url(url)
        return self.log_response(self.sesh.get(url, timeout=self.basic_timeout))

    def post(self, url, data=None, json=None):
        url = self.build_url(url)
        kwargs = {'timeout': self.post_timeout}
        if json:
            kwargs['json'] = json
        else:
            kwargs['data'] = data
        return self.log_response(self.sesh.post(url, **kwargs))

    def log_response(self, response):
        logging.debug(f'Response HTTP {response.status_code}: {response.text}')
        return response

    def build_url(self, url):
        url = url[1:] if url.startswith('/') else url
        url = url[:-1] if url.endswith('/') else url
        return '/'.join((self.base_url, url)) + '/'


def get_sal_client():
    global _client_instance
    if _client_instance is None:
        _client_instance = SalClient()
    return _client_instance
