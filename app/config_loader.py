# 設定ファイルの読み込みプログラム

import json
import os

CONFIG_PATHS = [
    "/boot/firmware/config.json",
    "/boot/config.json"
]

DEFAULT_CONFIG_PATH = "/home/jkkb/LoRaCam/config_template.json"            

def load_config():
    print("Config Loading...")
    # 設定ファイルの存在を確認
    config_path = None
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            print("Config file found !")
            config_path = path
            break

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            print("Config file correctly Loaded !")
            return config
    except Exception as e:
        with open(DEFAULT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
            print("Failed to load config, using default")
            return config
