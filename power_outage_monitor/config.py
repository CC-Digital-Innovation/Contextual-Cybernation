import yaml

config = {}

def set_config(file):
    with open(file) as fp:
        config.update(yaml.safe_load(fp))
