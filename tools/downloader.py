from __future__ import annotations

import os.path
from typing import TYPE_CHECKING
import requests

if TYPE_CHECKING:
    from core.content_extractor import ContentExtractor


def create_windows_shortcut_from_url(url: str, shortcut_path: str):
    """
    Creates a Windows shortcut (.lnk) file from a URL.
    :param url: The URL to create the shortcut from.
    :param shortcut_path: The path to save the shortcut to.
    """
    import win32com.client
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = url
    shortcut.save()



class DownloaderMixin:


    def download(self, content_extractor: ContentExtractor, directory: str):
        for document in content_extractor.get_document_objects():
            if not document.title:
                raise "No Document Title"

            if not directory:
                directory = r"../output/files"
            full_file_path = os.path.join(directory, document.title)
            self._download_file(document.url, full_file_path)

            print(document.url, document.title)


    def _download_file(self, url, filename:str):
        response = requests.get(url, stream=True, verify=True)

        if response.status_code in [404, 403, 400, 401]:


        response.raise_for_status()

        with open(filename, 'wb') as file:

            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    file.flush()
                    os.fsync(file.fileno())
        return filename



