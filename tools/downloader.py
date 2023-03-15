from __future__ import annotations

import os.path
from typing import TYPE_CHECKING
import requests

if TYPE_CHECKING:
    from core.content_extractor import ContentExtractor


class DownloaderMixin:


    def download(self, content_extractor: ContentExtractor, directory: str):
        for document in content_extractor.get_document_objects():
            if not document.title:
                raise "No Document Title"

            download_location = r"C:\Users\913678186\Desktop\test"
            full_file_path = os.path.join(download_location, document.title)
            self._download_file(document.url, full_file_path)

            print(document.url, document.title)


    def _download_file(self, url, filename:str):
        response = requests.get(url, stream=True, verify=True)
        response.raise_for_status()
        with open(filename, 'wb') as file:

            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    file.flush()
                    os.fsync(file.fileno())




