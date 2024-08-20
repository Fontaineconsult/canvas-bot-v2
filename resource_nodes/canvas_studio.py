from config.yaml_io import read_config
from core.content_scaffolds import get_source_page_url
from resource_nodes.base_node import Node
from network.studio_api import get_course, get_collection_media, get_media_sources_by_id, get_captions_by_media_id, \
    get_media_by_id, get_media_perspectives_by_id, get_media_perspectives_by_id
from tools.animation import animate


config = read_config()

instructure_perspectives_url = config['source_url_configs']['instructure_perspectives']


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
                    perspective = get_media_perspectives_by_id(media['id'])

                    media_uuid = perspective['perspectives'][0]['uuid']

                    if media_source:
                        for source in media_source['sources']:

                            if source.get('definition') == "low": # we just want the smallest file size
                                download_url = source['url']
                                mime_type = source['mime_type']
                            else:
                                download_url = media_source['sources'][0]["url"]
                                mime_type = media_source['sources'][0]['mime_type']

                        content_node = get_content_node(download_url)

                        url = f"{instructure_perspectives_url}{media_uuid}"

                        if len(captions['caption_files']) > 0:
                            media['mime_type'] = mime_type
                            node_to_append = content_node(self, self.root, media, url,
                                                          media['title'], captioned=True)

                            node_to_append.captions_list = captions['caption_files']
                            node_to_append.download_url = download_url
                            node_to_append.is_canvas_studio_file = True


                            rectify_studio_embeds(self, media['id'], node_to_append)

                        else:
                            media['mime_type'] = mime_type
                            node_to_append = content_node(self, self.root, media, url,
                                                          media['title'])
                            node_to_append.download_url = download_url
                            node_to_append.is_canvas_studio_file = True
                            rectify_studio_embeds(self, media['id'], node_to_append)

                        if content_node:
                            self.children.append(node_to_append)


def rectify_studio_embeds(self, media_id, node_to_append):

    embeds = self.root.manifest.get_content_nodes("CanvasStudioEmbed")

    for embed_item in embeds:

        if str(embed_item.id) == str(media_id):
            node_to_append.parent = embed_item.parent



