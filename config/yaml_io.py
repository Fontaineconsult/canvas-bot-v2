import yaml
import os
import re
import shutil, ctypes


def _substitute_placeholders(data, env_vars=None):
    """
    Recursively substitute {PLACEHOLDER} patterns with environment variable values.
    If env_vars dict is provided, use it; otherwise fall back to os.environ.
    """
    if env_vars is None:
        env_vars = os.environ

    if isinstance(data, str):
        # Find all {PLACEHOLDER} patterns and replace with env values
        def replace_match(match):
            key = match.group(1)
            return env_vars.get(key, match.group(0))  # Keep original if not found
        return re.sub(r'\{([A-Z_]+)\}', replace_match, data)
    elif isinstance(data, list):
        return [_substitute_placeholders(item, env_vars) for item in data]
    elif isinstance(data, dict):
        return {k: _substitute_placeholders(v, env_vars) for k, v in data.items()}
    else:
        return data


def read_config(substitute=False):
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"config.yaml"), "r", encoding='utf_8') as f:
        data = yaml.safe_load(f)
    if substitute:
        return _substitute_placeholders(data)
    return data


def read_re(substitute=True):
    """
    Read regex patterns from re.yaml.
    By default, substitutes {PLACEHOLDER} patterns with environment variable values.
    """
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"re.yaml"), "r") as f:
        data = yaml.safe_load(f)
    if substitute:
        return _substitute_placeholders(data)
    return data

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

        ctypes.windll.kernel32.SetFileAttributesW(os.path.join(course_folder, ".manifest"), 0x02)

