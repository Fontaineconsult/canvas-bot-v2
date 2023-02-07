from urllib.parse import urljoin, urlparse


def sort_nodes(self, **kwargs):

    for count, link in enumerate(self.node_links):
        canvas_resource_node = canvas_resource_identifier()

        if canvas_resource_node is not None:

            if isinstance(canvas_resource_node, PageNode):
                if canvas_resource_node.node_init_failed is not True:
                    self.children.append(canvas_resource_node)

            if isinstance(canvas_resource_node, str):
                self.node_links.append(canvas_resource_node)












































    # for count, link in enumerate(self.node_links):
    #     if not self.content_manifest.exists(link, self):
    #
    #         if "bypass_web_video_nodes" not in kwargs.keys():
    #             is_web_video = web_video_identifier(link, self.session, self, self.root)
    #             if is_web_video:
    #
    #                 self.content_manifest.add_item_to_manifest(is_web_video)
    #                 self.children.append(is_web_video)
    #
    #         if "bypass_web_audio_nodes" not in kwargs.keys():
    #             is_web_audio = web_audio_identifier(link, self.session, self, self.root)
    #             if is_web_audio:
    #
    #                 self.content_manifest.add_item_to_manifest(is_web_audio)
    #                 self.children.append(is_web_audio)
    #
    #         if "bypass_document_file_nodes" not in kwargs.keys():
    #             is_file = document_file_identifier(link, self.session, self, self.root)
    #             if is_file:
    #
    #                 self.content_manifest.add_item_to_manifest(is_file)
    #                 self.children.append(is_file)
    #
    #         if "bypass_canvas_file_nodes" not in kwargs.keys():
    #             no_query_params = urljoin(link, urlparse(link).path)
    #             is_canvas_file = canvas_file_indentifier(no_query_params, self.session, self, self.root)
    #
    #             if is_canvas_file:
    #
    #                 self.content_manifest.add_item_to_manifest(is_canvas_file)
    #                 self.children.append(is_canvas_file)
    #
    #         if "bypass_canvas_user_file_nodes" not in kwargs.keys():
    #             is_canvas_user_file = canvas_user_file_identifer(link, self.session, self, self.root)
    #
    #             if is_canvas_user_file:
    #
    #                 self.content_manifest.add_item_to_manifest(is_canvas_user_file)
    #                 self.children.append(is_canvas_user_file)
    #
    #         if "bypass_video_file_nodes" not in kwargs.keys():
    #             is_video_file = video_file_identifier(link, self.session, self, self.root)
    #             if is_video_file:
    #
    #                 self.content_manifest.add_item_to_manifest(is_video_file)
    #                 self.children.append(is_video_file)
    #
    #         if "bypass_audio_file_nodes" not in kwargs.keys():
    #             is_audio_file = audio_file_identifier(link, self.session, self, self.root)
    #             if is_audio_file:
    #
    #                 self.content_manifest.add_item_to_manifest(is_audio_file)
    #                 self.children.append(is_audio_file)
    #
    #         if "bypass_image_file_nodes" not in kwargs.keys():
    #             is_image_file = image_file_identifier(link, self.session, self, self.root)
    #             if is_image_file:
    #
    #                 self.content_manifest.add_item_to_manifest(is_image_file)
    #                 self.children.append(is_image_file)
    #
    #
    #         if "bypass_google_docs" not in kwargs.keys():
    #             is_google_doc = google_doc_identifier(self.session,
    #                                                   link,
    #                                                   self.root,
    #                                                   self,
    #                                                   self.page_manifest,
    #                                                   self.content_manifest,
    #                                                   self.junk_manifest,
    #                                                   **self.kwargs)
    #             if is_google_doc:
    #                 self.page_manifest.add_item_to_manifest(is_google_doc)
    #                 self.children.append(is_google_doc)
    #
    #
    #         if "bypass_additional_nodes" not in kwargs.keys():
    #
    #             is_additional_page = additional_page_identifier(self.session,
    #                                                             link,
    #                                                             self.root,
    #                                                             self,
    #                                                             self.page_manifest,
    #                                                             self.content_manifest,
    #                                                             self.junk_manifest,
    #                                                             **self.kwargs)
    #
    #             if is_additional_page:
    #
    #                 self.page_manifest.add_item_to_manifest(is_additional_page)
    #                 self.children.append(is_additional_page)
    #
    #         if "bypass_external_nodes" not in kwargs.keys():
    #
    #             if link not in self.junk_manifest or not self.content_manifest.exists(link, self):
    #
    #                 is_external_resource = external_resource_identifier(self.session,
    #                                                                     link,
    #                                                                     self.root,
    #                                                                     self,
    #                                                                     self.page_manifest,
    #                                                                     self.content_manifest,
    #                                                                     self.junk_manifest,
    #                                                                     **self.kwargs)
    #                 if is_external_resource:
    #                     self.junk_manifest.append(link)
    #                     # self.content_manifest.add_item_to_manifest(is_external_resource)
    #                     self.children.append(is_external_resource)
