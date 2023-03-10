from typing import List
import inspect
from content_scaffolds import *
from core.manifest import Manifest
from resource_nodes.content_nodes import *



class ContentExtractor:


    def __init__(self, manifest: Manifest):
        self.manifest = manifest


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


    def build_document_dict(self):
        for document in self.get_document_objects():
            print(document_dict(document))

    def build_videos_dict(self):
        for video_site in self.get_video_site_objects():
            print(video_site_dict(video_site))

        for video_file in self.get_video_file_objects():
            print(video_file_dict(video_file))
