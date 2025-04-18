from json import JSONDecodeError
from urllib.parse import urljoin

import requests
from django.conf import settings


class InvalidPostcodeError(Exception):
    pass


class InvalidUprnError(Exception):
    pass


class DevsDCAPIException(Exception):
    def __init__(self, response: requests.Response):
        try:
            self.message = {"error": response.json().get("message", "")}
        except (JSONDecodeError, AttributeError):
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

    def make_request(self, postcode, uprn=None, **extra_params):
        base = urljoin(self.API_BASE, "/api/v1/")
        path = f"postcode/{postcode}/"
        if uprn:
            path = f"address/{uprn}/"
        url = urljoin(base, path)

        default_params = {"auth_token": self.API_KEY, "include_current": 1}
        if extra_params:
            default_params.update(**extra_params)
        resp = requests.get(url, params=default_params)
        if path.startswith("postcode/") and resp.status_code == 400:
            raise InvalidPostcodeError()
        if path.startswith("address/") and resp.status_code == 404:
            raise InvalidUprnError()
        if resp.status_code >= 400:
            raise DevsDCAPIException(response=resp)
        return resp.json()
