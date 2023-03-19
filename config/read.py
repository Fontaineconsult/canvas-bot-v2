import yaml
import os

def read_config():
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"config.yaml"), "r", encoding='utf_8') as f:
        return yaml.safe_load(f)

def read_re():
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"re.yaml"), "r") as f:
        return yaml.safe_load(f)

def create_yaml_file(filename, data):
    with open(filename, "w") as f:
        yaml.dump(data, f)