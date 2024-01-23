import json, os

from config.yaml_io import create_download_manifest
from core.content_scaffolds import *
from core.manifest import Manifest
from resource_nodes.content_nodes import *
from core.downloader import DownloaderMixin
import shutil

from tools.export_to_excel import save_as_excel


class ContentExtractor(DownloaderMixin):

    """
    This class is responsible for extracting content from a course and saving it to a folder.
    """


    def __init__(self, manifest: Manifest, course_id, course_url, course_name, exists):
        self.manifest = manifest
        self.course_id = course_id
        self.course_url = course_url
        self.course_name = course_name
        self.exists = exists

    def get_document_objects(self):
        return [item for item in self.manifest.content_list() if isinstance(item, Document)]

    def get_video_file_objects(self):
        return [item for item in self.manifest.content_list() if isinstance(item, VideoFile)
                or isinstance(item, CanvasStudioEmbed)]

    def get_video_site_objects(self):
        return [item for item in self.manifest.content_list() if isinstance(item, VideoSite)]

    def get_audio_file_objects(self):
        return [item for item in self.manifest.content_list() if isinstance(item, AudioFile)]

    def get_audio_site_objects(self):
        return [item for item in self.manifest.content_list() if isinstance(item, AudioSite)]

    def get_image_file_objects(self):
        return [item for item in self.manifest.content_list() if isinstance(item, ImageFile)]

    def get_document_site_objects(self):
        return [item for item in self.manifest.content_list() if isinstance(item, DocumentSite)]

    def get_digital_textbook_objects(self):
        return [item for item in self.manifest.content_list() if isinstance(item, DigitalTextbook)]

    def get_file_storage_site_objects(self):
        return [item for item in self.manifest.content_list() if isinstance(item, FileStorageSite)]

    def get_unsorted_objects(self):
        return [item for item in self.manifest.content_list() if isinstance(item, Unsorted)]

    def build_documents_dict(self, file_download_directory, flatten):

        return {
            "documents": [document_dict(document, file_download_directory, flatten) for document in self.get_document_objects()],
            "document_sites": [document_site_dict(document_site) for document_site in self.get_document_site_objects()],
        }

    def build_videos_dict(self, file_download_directory, flatten, check_video_site_caption_status):

        return {
            "video_sites": [video_site_dict(video_site, check_video_site_caption_status)
                            for video_site in self.get_video_site_objects()],
            "video_files": [video_file_dict(video_file, file_download_directory, flatten) for video_file in
                            self.get_video_file_objects()],
        }

    def build_audio_dict(self, file_download_directory, flatten):

        return {
            "audio_sites": [audio_site_dict(audio_site) for audio_site in self.get_audio_site_objects()],
            "audio_files": [audio_file_dict(audio_file, file_download_directory, flatten) for audio_file in
                            self.get_audio_file_objects()],
        }

    def build_images_dict(self, file_download_directory, flatten):

        return {
            "image_files": [image_file_dict(image_file, file_download_directory, flatten) for image_file in
                            self.get_image_file_objects()],
        }

    def build_unsorted_dict(self):

        return {
            "unsorted": [unsorted_dict(unsorted) for unsorted in self.get_unsorted_objects()],
        }

    def get_all_content(self, file_download_directory=None, **params):
        flatten = params.get("flatten", False)
        check_video_site_caption_status = params.get("check_video_site_caption_status", False)
        main_dict = {
            "course_id": self.course_id,
            "course_url": self.course_url,
            "course_name": self.course_name,
            "content":{
                "documents": self.build_documents_dict(file_download_directory, flatten),
                "videos": self.build_videos_dict(file_download_directory, flatten, check_video_site_caption_status),
                "audio": self.build_audio_dict(file_download_directory, flatten),
                "images": self.build_images_dict(file_download_directory, flatten),
                "unsorted": self.build_unsorted_dict()
            }
        }
        return main_dict

    def get_all_content_as_json(self, file_download_directory, **params):
        return json.dumps(self.get_all_content(file_download_directory, **params), indent=4, sort_keys=True, default=str)

    def save_content_as_json(self, json_save_directory, file_download_directory,  **params):

        """
        Saves all content as a json file.
        :param directory:
        :return:
        """

        if self.exists:
            dirname = os.path.abspath(__file__ + "/../../")
            full_path = os.path.join(dirname, rf'output\\json\\{self.course_id}.json')

            if json_save_directory:
                full_path = os.path.join(json_save_directory, rf"{self.course_id}.json")

            if os.path.exists(full_path):
                os.remove(full_path)

            if not os.path.exists(os.path.dirname(full_path)):
                os.makedirs(os.path.dirname(full_path))

            with open(full_path, 'w') as f:

                f.write(self.get_all_content_as_json(file_download_directory,**params))
                f.close()

            return full_path

    def save_content_as_excel(self, excel_directory, **params):

        """
        Saves all content as an excel file.
        :param directory:
        :return:
        """
        file_download_directory = params.get("download_folder", None)
        download_hidden_files = params.get("download_hidden_files", False)


        if self.exists:
            root_download_directory = os.path.join(excel_directory, rf"{sanitize_windows_filename(self.course_name)} "
                                                              rf"- {self.course_id}")

            if file_download_directory:
                root_file_download_directory = os.path.join(file_download_directory, rf"{sanitize_windows_filename(self.course_name)} "
                                                                                     rf"- {self.course_id}")
            else:
                root_file_download_directory = None

            if not os.path.exists(root_download_directory):
                os.makedirs(root_download_directory)
            json_data = json.loads(self.get_all_content_as_json(root_file_download_directory, **params))

            save_as_excel(json_data, root_download_directory, download_hidden_files)

    def download_files(self, directory, **params):

        """
        Downloads all files in the course.
        :param directory:
        :param args:
        :return:
        """

        flush_after_download = params.get("flush_after_download", False)

        if self.exists:
            root_download_directory = os.path.join(directory, rf"{sanitize_windows_filename(self.course_name)} "
                                                              rf"- {self.course_id}")
            create_download_manifest(root_download_directory)
            self.download(self, root_download_directory, **params)

            if flush_after_download:
                self.clear_folder_contents(directory)

    def clear_folder_contents(self, directory):
        """
        Clears the contents of a folder, but not the folder itself. BE VERY CAREFUL WITH THIS FUNCTION.
        directory: The directory containing the course folder to clear.
        """
        if self.exists:
            root_download_directory = os.path.join(directory, rf"{sanitize_windows_filename(self.course_name)} "
                                                              rf"- {self.course_id}")
            for root, dirs, files in os.walk(root_download_directory, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            shutil.rmtree(root_download_directory)