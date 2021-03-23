from core.mixins import ReadFromUrlMixin, ReadFromFileMixin


class HustingImporter(ReadFromUrlMixin, ReadFromFileMixin):
    def __init__(self, url=None, file_path=None):
        self.url = url
        self.file_path = file_path

    @property
    def rows(self):
        if self.file_path:
            yield from self.read_from_file(path_to_file=self.file_path)
        else:
            yield from self.read_from_url(url=self.url)
