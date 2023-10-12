from core.content_scaffolds import get_source_page_url
from resource_nodes.base_node import Node
from network.studio_api import get_course, get_collection_media, get_media_sources_by_id, get_captions_by_media_id, \
    get_media_by_id
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

        if course:
            collection_id = course['course']['id']
            collection = get_collection_media(collection_id)

            if collection['meta']['total_count'] > 0:
                for media in collection['media']:

                    captions = get_captions_by_media_id(media['id'])
                    media_source = get_media_sources_by_id(media['id'])

                    if media_source:
                        for source in media_source['sources']:

                            if source.get('definition') == "low": # we just want the smallest file size
                                url = source['url']
                            else:
                                url = media_source['sources'][0]["url"]

                        content_node = get_content_node(url)

                        if len(captions['caption_files']) > 0:

                            node_to_append = content_node(self, self.root, media, url,
                                                          media['title'], captioned=True)

                            node_to_append.captions_list = captions['caption_files']

                            rectify_studio_embeds(self, media['id'], node_to_append)

                        else:
                            node_to_append = content_node(self, self.root, media, url,
                                                          media['title'])
                            rectify_studio_embeds(self, media['id'], node_to_append)

                        if content_node:
                            self.children.append(node_to_append)


def rectify_studio_embeds(self, media_id, node_to_append):

    embeds = self.root.manifest.get_content_nodes("CanvasStudioEmbed")

    for item in embeds:
        if str(item.canvas_studio_id) == str(media_id):
            node_to_append.parent = item.parent



