from __future__ import annotations

from os import path

from sorters.sorters import force_to_shortcut, file_name_extractor
from datetime import datetime

import win32com.client
import os.path
from typing import TYPE_CHECKING
import requests
from requests.exceptions import MissingSchema, InvalidURL
from config.yaml_io import read_config, read_download_manifest, write_to_download_manifest
from tools.string_checking.url_cleaning import sanitize_windows_filename

config = read_config()

user_agent = config['requests']['user-agent']
default_download_path = config['default_download_path']

from core.content_scaffolds import is_hidden, build_path
from tools.string_checking.other_tools import has_file_extension, remove_query_params_from_url

if TYPE_CHECKING:
    from core.content_extractor import ContentExtractor


def sort_by_date():
    return datetime.now().strftime('%d-%m-%Y')




def path_constructor(root_directory, node, filename, flatten: bool):

    """
        Returns the path to the folder that the node should be saved in.
    """
    node_path = build_path(node, ignore_root=True)
    paths = list()

    if flatten:
        paths.append(sanitize_windows_filename(node.title[:50]).rstrip() if node.title else str(node.__class__.__name__))
        return os.path.join(root_directory, sort_by_date(), filename)

    for node in node_path:
        if hasattr(node, 'is_resource'):
            paths.append(sanitize_windows_filename(node.title[:50]).rstrip() if node.title else str(node.__class__.__name__))
    return os.path.join(root_directory, sort_by_date(), *paths[::-1], filename)


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
        include_video_files, include_audio_files, flatten, flush_after_download, download_hidden_files = args

        if not directory:
            print(f"Using default download path: {os.path.dirname(os.path.abspath(__file__))}")
            directory = os.path.dirname(os.path.abspath(__file__))

        download_nodes = [ContentNode for ContentNode in content_extractor.get_document_objects()]

        if include_video_files:
            download_nodes.extend([ContentNode for ContentNode in content_extractor.get_video_file_objects()])

        if include_audio_files:
            download_nodes.extend([ContentNode for ContentNode in content_extractor.get_audio_file_objects()])

        for ContentNode in download_nodes:
            if is_hidden(ContentNode):
                if download_hidden_files:
                    print(f"Including hidden file: {ContentNode.title} {ContentNode.url}\n")
                else:
                    continue

            if ContentNode.url in download_manifest:
                print(f"Skipping {ContentNode.url} because it has already been downloaded.")
                continue

            if not has_file_extension(ContentNode.title):
                title = remove_query_params_from_url(file_name_extractor.match(ContentNode.url.split('/')[-1]).group(0))
            else:
                title = sanitize_windows_filename(file_name_extractor.match(ContentNode.title).group(0))

            full_file_path = path_constructor(directory,
                                              ContentNode,
                                              title,
                                              flatten)

            self._download_file(ContentNode.url, full_file_path, bool(force_to_shortcut.match(ContentNode.url)))

            download_manifest.append(ContentNode.url)

        write_to_download_manifest(directory, "downloaded_files", download_manifest)

    def _download_file(self, url, filename:str, force_to_shortcut=False):

        """
        Downloads a file from a URL to a specified location.
        :param url:
        :param filename:
        :param force_to_shortcut:
        :return:
        """

        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

        if force_to_shortcut:
            return create_windows_shortcut_from_url(url, f"{filename}.lnk")


        try:
            response = requests.get(url, stream=True, verify=True, headers=user_agent)

            if response.status_code in [401, 402, 403, 404, 405, 406]:

                print(f"Response Error {response.status_code} {response.reason} {url} {filename}\n")
                return create_windows_shortcut_from_url(url, f"{filename}.lnk")
            else:
                try:
                    print(f"Downloading {url} to {filename}...\n")
                    with open(filename, 'wb') as file:

                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                file.write(chunk)
                                file.flush()
                                os.fsync(file.fileno())

                    return filename

                except PermissionError:
                    print(f"Permission Error: {filename}\n")
                    return create_windows_shortcut_from_url(url, f"{filename}.lnk")

        except requests.exceptions.ConnectionError as exc:
            print(f"Connection Error: {exc}, {url}\n")
            return create_windows_shortcut_from_url(url, f"{filename}.lnk")

        except MissingSchema as exc:
            print(f"Missing Schema Error: {exc}, {url}\n")

        except InvalidURL as exc:
            print(f"Invalid URL Error: {exc}, {url}\n")






