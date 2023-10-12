import re
from config.yaml_io import read_re

expressions = read_re()


def re_combiner(re_list):

    raw_string = "|".join(re_list)
    return re.compile(raw_string, re.IGNORECASE)


resource_node_regex = re.compile(re_combiner(expressions["resource_node_types_re"]))

document_content_regex = re_combiner(expressions["document_content_regex"])

image_content_regex = re_combiner(expressions["image_content_regex"])

web_video_content_regex = re_combiner(expressions["web_video_resources_regex"])

video_file_content_regex = re_combiner(expressions["video_file_resources_regex"])

web_audio_content_regex = re_combiner(expressions["web_audio_resources_regex"])

audio_file_content_regex = re_combiner(expressions["audio_file_resources_regex"])

web_document_applications_regex = re_combiner(expressions["web_document_applications_regex"])

canvas_studio_embed = re_combiner(expressions["canvas_studio_embed"])

file_storage_regex = re_combiner(expressions["file_storage_regex"])

ignore_list_regex = re_combiner(expressions['ignore_list_regex'])

force_to_shortcut = re_combiner(expressions['force_to_shortcut'])

file_name_extractor = re_combiner([document_content_regex.pattern + "|" +
                                   image_content_regex.pattern + "|" +
                                   video_file_content_regex.pattern + "|" +
                                   audio_file_content_regex.pattern])

