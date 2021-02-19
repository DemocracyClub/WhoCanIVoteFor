import csv
import requests


class ReadFromUrlMixin:
    def read_from_url(self, url):
        with requests.get(url, stream=True) as r:
            r.encoding = "utf-8"
            yield from csv.DictReader(r.iter_lines(decode_unicode=True))


class ReadFromFileMixin:
    def read_from_file(self, path_to_file):
        with open(path_to_file, "r") as fh:
            reader = csv.DictReader(fh)
            yield from reader
