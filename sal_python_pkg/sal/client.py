import logging

import macsesh

from sal.utils import pref


class SalClient():

    basic_timeout = (3.05, 4)
    post_timeout = (3.05, 8)
    base_url = ''

    def __init__(self):
        sesh = macsesh.KeychainSession()
        # sesh = macsesh.SecureTransportSession()

        base_url = pref('ServerURL')
        self.base_url = base_url if not base_url.endswith('/') else base_url[:-1]

        ca_cert = pref('CACert')
        if ca_cert:
            sesh.verify = ca_cert

        basic_auth = pref('BasicAuth')
        if basic_auth:
            key = pref('key', '')
            sesh.auth = ('sal', key)

        # TODO: Handle keychain-based certs.
        ssl_client_cert = pref('SSLClientCertificate')
        ssl_client_key = pref('SSLClientKey')
        if ssl_client_cert:
            sesh.cert = (ssl_client_cert, ssl_client_key) if ssl_client_key else ssl_client_cert

        self.sesh = sesh

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
