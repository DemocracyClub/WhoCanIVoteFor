from json import JSONDecodeError
from urllib.parse import urljoin

import requests

from django.conf import settings


class DevsDCAPIException(Exception):
    def __init__(self, response: requests.Response):
        try:
            self.message = {"error": response.json().get("message", "")}
        except JSONDecodeError:
            self.message = ""
        self.status = response.status_code
        self.response = response


class DevsDCClient:
    def __init__(self, api_base=None, api_key=None):
        if not api_base:
            api_base = settings.DEVS_DC_BASE
        self.API_BASE = api_base
        if not api_key:
            api_key = settings.DEVS_DC_API_KEY
        self.API_KEY = api_key

    def make_request(self, postcode, uprn=None):
        path = f"/api/v1/postcode/{postcode}/"
        if uprn:
            path = f"/api/v1/address/{uprn}/"
        url = urljoin(self.API_BASE, path)
        req = requests.get(
            url, params={"auth_token": self.API_KEY, "include_current": 1}
        )
        if req.status_code >= 400:
            raise DevsDCAPIException(response=req)
        return req.json()
