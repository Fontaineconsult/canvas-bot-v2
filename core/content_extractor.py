from typing import List
import inspect
from content_scaffolds import *
from core.manifest import Manifest
from resource_nodes.canvasfiles import CanvasFile
from resource_nodes.content_nodes import Document


def build_path(node) -> List:
    path_list = list()

    def get_parent(node):

        if hasattr(node, "root_node"):
            path_list.append(node)
        if not hasattr(node, "root_node"):
            path_list.append(node)
            get_parent(node.parent)

    get_parent(node)
    return path_list





class ContentExtractor:



    def __init__(self, manifest: Manifest):
        self.manifest = manifest


    def get_canvas_files(self):
        for item in self.manifest.content_list():
            if isinstance(item, CanvasFile):
                pass

