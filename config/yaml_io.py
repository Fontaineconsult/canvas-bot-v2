import yaml
import os
import shutil

def read_config():
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"config.yaml"), "r", encoding='utf_8') as f:
        return yaml.safe_load(f)

def read_re():
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"re.yaml"), "r") as f:
        return yaml.safe_load(f)

def read_download_manifest(course_folder):
    with open(os.path.join(course_folder, ".manifest", "download_manifest.yaml"), "r+") as f:
        return yaml.safe_load(f)

def write_to_download_manifest(course_folder: str, heading:str, content_list: list):
    yaml_content = {"downloaded_files": content_list}

    with open(os.path.join(course_folder, ".manifest", "download_manifest.yaml"),"w") as f:
        yaml.dump(yaml_content, f, default_flow_style=False, allow_unicode=True)

def create_download_manifest(course_folder: str):

    if not os.path.exists(os.path.join(course_folder, ".manifest")):
        os.makedirs(os.path.join(course_folder, ".manifest"), exist_ok=True)

    raw_manifest_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download_manifest.yaml")
    if not os.path.exists(os.path.join(course_folder, ".manifest", "download_manifest.yaml")):
        shutil.copy(raw_manifest_path, os.path.join(course_folder, ".manifest", "download_manifest.yaml"))



