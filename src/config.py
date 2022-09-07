from pathlib import PurePath

import yaml

with open(PurePath(__file__).with_name('config.yaml')) as fp:
    config = yaml.safe_load(fp)
