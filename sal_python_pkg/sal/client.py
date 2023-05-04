import logging
import os

try:
    from macsesh import Session as MacSeshSession
except ImportError:
    MacSeshSession = None
import requests


_client_instance = None


class SalClient:
    session_class = requests.Session
    _base_url = ""
    _auth = None
    _cert = None
    _verify = None
    basic_timeout = (3.05, 4)
    post_timeout = (3.05, 8)

    def __init__(self):
        self.create_session()

    def create_session(self):
        self.session = self.session_class()
        if self.auth:
            self.session.auth = self._auth
        if self.cert:
            self.session.cert = self._cert
        if self.verify:
            self.session.verify = self._verify

            # self.session.cert = (self._cert, self._key) if self._key else self._cert

    @property
    def base_url(self):
        return self._base_url

    @base_url.setter
    def base_url(self, base_url):
        self._base_url = base_url if not base_url.endswith("/") else base_url[:-1]

    @property
    def auth(self):
        return self._auth

    @auth.setter
    def auth(self, creds):
        self._auth = creds
        self.create_session()

    @property
    def cert(self):
        return self._cert

    @cert.setter
    def cert(self, cert, key=None):
        self._cert = (cert, key) if key else cert
        self.create_session()

    @property
    def verify(self):
        return self._verify

    @verify.setter
    def verify(self, path):
        self._verify = path
        self.create_session()

    def get(self, url):
        url = self.build_url(url)
        return self.log_response(self.session.get(url, timeout=self.basic_timeout))

    def post(self, url, data=None, json=None):
        url = self.build_url(url)
        kwargs = {"timeout": self.post_timeout}
        if json:
            kwargs["json"] = json
        else:
            kwargs["data"] = data
        return self.log_response(self.session.post(url, **kwargs))

    def log_response(self, response):
        logging.debug(f"Response HTTP {response.status_code}: {response.text}")
        return response

    def build_url(self, url):
        url = url[1:] if url.startswith("/") else url
        url = url[:-1] if url.endswith("/") else url
        return "/".join((self.base_url, url)) + "/"


class MacKeychainClient(SalClient):
    session_class = MacSeshSession


def get_sal_client(with_client_class=None):
    global _client_instance
    if _client_instance is None or (
        with_client_class is not None
        and not isinstance(_client_instance, with_client_class)
    ):
        _client_instance = (
            with_client_class() if with_client_class is not None else SalClient()
        )
    return _client_instance
