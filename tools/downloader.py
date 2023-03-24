from __future__ import annotations

import warnings
from datetime import datetime

import win32com.client
import os.path
from typing import TYPE_CHECKING
import requests
from config.yaml_io import read_config, read_download_manifest, write_to_download_manifest
from tools.string_checking.url_cleaning import sanitize_windows_filename

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
    """
    A mixin class for the ContentExtractor class that provides methods for downloading files.
    """


    def download(self, content_extractor: ContentExtractor, directory: str, *args):

        download_manifest = read_download_manifest(directory)['downloaded_files']

        include_video_files, include_audio_files = args if args else (False, False)

        if not directory:
            print(f"Using default download path: {default_download_path}")
            directory = default_download_path

        download_nodes = [ContentNode for ContentNode in content_extractor.get_document_objects()]

        if include_video_files:
            download_nodes.extend([ContentNode for ContentNode in content_extractor.get_video_file_objects()])

        if include_audio_files:
            download_nodes.extend([ContentNode for ContentNode in content_extractor.get_audio_file_objects()])

        for ContentNode in download_nodes:

            if is_hidden(ContentNode):
                continue

            if ContentNode.url in download_manifest:
                print(f"Skipping {ContentNode.url} because it has already been downloaded.")
                continue

            if not has_file_extension(ContentNode.title):
                title = remove_query_params_from_url(ContentNode.url.split('/')[-1])
            else:
                title = sanitize_windows_filename(ContentNode.title)

            full_file_path = os.path.join(directory, path_configs['sort-by-date'],
                                          f"{ContentNode.__class__.__name__}s",
                                          sanitize_windows_filename(title))

            self._download_file(ContentNode.url, full_file_path)

            download_manifest.append(ContentNode.url)

        write_to_download_manifest(directory, "downloaded_files", download_manifest)




    def _download_file(self, url, filename:str):
        """
        Downloads a file from a URL to a specified location.
        :param url:
        :param filename:
        :return:
        """

        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

        print(f"Downloading {url} to {filename}...")
        try:
            response = requests.get(url, stream=True, verify=True, headers=user_agent)
        except requests.exceptions.ConnectionError as exc:
            print(f"Connection Error: {exc}")

            return create_windows_shortcut_from_url(url, f"{filename}.lnk")

        if response.status_code in [401, 402, 403, 404, 405, 406]:

            print(f"Error {response.status_code} {response.reason} {url} {filename}")
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
            print(f"Permission Error: {filename}")
            return create_windows_shortcut_from_url(url, f"{filename}.lnk")


