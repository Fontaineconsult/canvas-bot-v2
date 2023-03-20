from __future__ import annotations

import warnings
from datetime import datetime

import win32com.client
import os.path
from typing import TYPE_CHECKING
import requests
from config.yaml_io import read_config, read_download_manifest, write_to_download_manifest

config = read_config()

user_agent = config['requests']['user-agent']
default_download_path = config['default_download_path']

from core.content_scaffolds import is_hidden
from tools.string_checking.other_tools import has_file_extension, remove_query_params_from_url

if TYPE_CHECKING:
    from core.content_extractor import ContentExtractor


def sort_by_date():
    return datetime.now().strftime('%d-%m-%Y')


path_configs = {
    'sort-by-date':sort_by_date()

}




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


    def download(self, content_extractor: ContentExtractor, directory: str, *args):
        download_manifest = read_download_manifest(directory)['downloaded_files']

        if not directory:
            warnings.warn(f"Using default download path: {default_download_path}", UserWarning)
            directory = default_download_path


        for ContentNode in content_extractor.get_document_objects():

            if is_hidden(ContentNode):
                continue

            if ContentNode.url in download_manifest:
                print(f"Skipping {ContentNode.url} because it has already been downloaded.")
                continue

            if not has_file_extension(ContentNode.title):
                title = remove_query_params_from_url(ContentNode.url.split('/')[-1])
            else:
                title = ContentNode.title

            full_file_path = os.path.join(directory, path_configs['sort-by-date'],title)

            self._download_file(ContentNode.url, full_file_path)

            download_manifest.append(ContentNode.url)

        write_to_download_manifest(directory, "downloaded_files", download_manifest)



    def _download_file(self, url, filename:str):

        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

        print(f"Downloading {url} to {filename}...")
        try:
            response = requests.get(url, stream=True, verify=True, headers=user_agent)
        except requests.exceptions.ConnectionError as exc:
            warnings.warn(f"Connection Error: {exc}", UserWarning)

            return create_windows_shortcut_from_url(url, f"{filename}.lnk")

        if response.status_code in [401, 402, 403, 404, 405, 406]:

            warnings.warn(f"Error {response.status_code} {response.reason} {url} {filename} {response.text}", UserWarning)
            return create_windows_shortcut_from_url(url, f"{filename}.lnk")

        try:
            with open(filename, 'wb') as file:

                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        file.flush()
                        os.fsync(file.fileno())

            return filename

        except PermissionError:
            warnings.warn(f"Permission Error: {filename}",UserWarning)
            return create_windows_shortcut_from_url(url, f"{filename}.lnk")


