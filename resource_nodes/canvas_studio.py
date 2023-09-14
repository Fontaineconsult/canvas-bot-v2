from resource_nodes.base_node import Node
from network.studio_api import get_course, get_collection_media, get_media_sources_by_id
from tools.animation import animate


class CanvasStudio(Node):



    def __init__(self, course_id, parent):

        super().__init__(parent, parent)
        self.course_id = course_id
        self.get_all_items()

    @animate('Importing Canvas Studio Media')
    def get_all_items(self):
        from core.node_factory import get_content_node
        course = get_course(self.course_id)

        if not course.get('error'):

            collection_id = course['course']['id']
            collection = get_collection_media(collection_id)
            if collection['meta']['total_count'] > 0:
                for media in collection['media']:
                    media_source = get_media_sources_by_id(media['id'])
                    content_node = get_content_node(media_source['sources'][0]['url'])
                    if content_node:
                        self.children.append(content_node(self, self.root, media, media['title'], media_source['sources'][0]['url']))

