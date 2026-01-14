# 設定ファイルの読み込みプログラム

import json
import os

CONFIG_PATHS = [
    "/boot/firmware/config.json",
    "/boot/config.json"
]

DEFAULT_CONFIG_PATH = "/home/jkkb/LoRaCam/config_template.json"            

def load_config():
    # 設定ファイルの存在を確認
    config_path = None
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            config_path = path
            break

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config
    except Exception as e:
        with open(DEFAULT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
            return config
