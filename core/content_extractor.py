import json, os
from typing import List
import inspect
from core.content_scaffolds import *
from core.manifest import Manifest
from resource_nodes.content_nodes import *



class ContentExtractor:


    def __init__(self, manifest: Manifest, course_id, course_url):
        self.manifest = manifest
        self.course_id = course_id
        self.course_url = course_url


    def get_document_objects(self):
        return [item for item in self.manifest.content_list() if isinstance(item, Document)]

    def get_video_file_objects(self):
        return [item for item in self.manifest.content_list() if isinstance(item, VideoFile)]

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

    def build_documents_dict(self):

        return {
            "documents": [document_dict(document) for document in self.get_document_objects()],
            "document_sites": [document_site_dict(document_site) for document_site in self.get_document_site_objects()],
        }

    def build_videos_dict(self):

        return {
            "video_sites": [video_site_dict(video_site) for video_site in self.get_video_site_objects()],
            "video_files": [video_file_dict(video_file) for video_file in self.get_video_file_objects()],
        }

    def build_audio_dict(self):

        return {
            "audio_sites": [audio_site_dict(audio_site) for audio_site in self.get_audio_site_objects()],
            "audio_files": [audio_file_dict(audio_file) for audio_file in self.get_audio_file_objects()],
        }

    def build_images_dict(self):

        return {
            "image_files": [image_file_dict(image_file) for image_file in self.get_image_file_objects()],
        }

    def build_unsorted_dict(self):

        return {
            "unsorted": [unsorted_dict(unsorted) for unsorted in self.get_unsorted_objects()],
        }


    def get_all_content(self, **kwargs):

        main_dict = {
            "course_id": self.course_id,
            "course_url": self.course_url,
            "content":{
                "documents": self.build_documents_dict(),
                "videos": self.build_videos_dict(),
                "audio": self.build_audio_dict(),
                "images": self.build_images_dict(),
                "unsorted": self.build_unsorted_dict()
            }
        }
        return main_dict

    def get_all_content_as_json(self):
        return json.dumps(self.get_all_content(), indent=4, sort_keys=True, default=str)

    def save_content_as_json(self, directory=None):
        dirname = os.path.abspath(__file__ + "/../../")
        full_path = os.path.join(dirname, f'output\\json\\{self.course_id}.json')

        if directory:
            full_path = os.path.join(directory, f"{self.course_id}.json")

        if os.path.exists(full_path):
            os.remove(full_path)

        with open(full_path, 'w') as f:
            f.write(self.get_all_content_as_json())
            f.close()

        return full_path

