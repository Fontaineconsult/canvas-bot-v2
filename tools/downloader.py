from __future__ import annotations
import win32com.client
import os.path
from typing import TYPE_CHECKING
import requests
from config.read import read_config

user_agent = read_config()['requests']['user-agent']


from core.content_scaffolds import is_hidden
from tools.string_checking.other_tools import has_file_extension

if TYPE_CHECKING:
    from core.content_extractor import ContentExtractor


def create_windows_shortcut_from_url(url: str, shortcut_path: str):
    """
    Creates a Windows shortcut (.lnk) file from a URL.
    :param url: The URL to create the shortcut from.
    :param shortcut_path: The path to save the shortcut to.
    """

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = url
    shortcut.save()
    return shortcut_path


class DownloaderMixin:

    def download(self, content_extractor: ContentExtractor, directory: str):
        for document in content_extractor.get_document_objects():

            if is_hidden(document):
                continue

            if not directory:
                directory = r"../output/files"

            if not has_file_extension(document.title):
                title = document.url.split('/')[-1]
            else:
                title = document.title
            full_file_path = os.path.join(directory, title)

            self._download_file(document.url, full_file_path)

    def _download_file(self, url, filename:str):

        try:
            response = requests.get(url, stream=True, verify=True, headers=user_agent)
            print(url, response.status_code)
        except requests.exceptions.ConnectionError as exc:
            print(f"Connection Error: {exc}")
            return create_windows_shortcut_from_url(url, f"{filename}.lnk")

        if response.status_code in [401, 402, 403, 404, 405, 406]:

            Warning(f"Error {response.status_code} {response.reason} {url} {filename} {response.text}")
            return create_windows_shortcut_from_url(url, f"{filename}.lnk")

        with open(filename, 'wb') as file:

            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    file.flush()
                    os.fsync(file.fileno())
        return filename



