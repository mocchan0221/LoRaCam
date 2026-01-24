import json
import os
import sys

class ConfigManager:
    CONFIG_PATH = "/boot/firmware/config.json"

    def __init__(self):
        self.config_data = {}

    def load(self):
        try:
            if os.path.exists(self.CONFIG_PATH):
                print(f"Config file found at: {self.CONFIG_PATH}")
                with open(self.CONFIG_PATH, 'r') as f:
                    self.config_data = json.load(f)
                    print("Config file correctly Loaded !")
            else:
                print(f"Config not found.")
                return None
        
        except Exception as e:
            print(f"[Error] Failed to load config: {e}")
            return None

        return self.config_data

    def save(self):
        print(f"Saving config to: {self.CONFIG_PATH}")
        try:

            with open(self.CONFIG_PATH, 'w') as f:
                json.dump(self.config_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            print("Config saved successfully.")
            return True
        except Exception as e:
            print(f"[Error] Failed to save config: {e}")
            return False

    def get(self, key, default=None):
        """設定値を取得するヘルパー"""
        return self.config_data.get(key, default)

    def update_status(self, is_latest_value: int):
        """is_latest フラグを更新して保存するショートカット"""
        self.set_nested(self.config_data, "Network.IsLatest", is_latest_value)
        return self.save()
    
    def set_nested(data, path, value, delimiter='.'):
        if not isinstance(path,str):
            raise TypeError(f"path must be str now its {type(path)}")
        keys = path.split(delimiter)
        
        current = data
        for key in keys[:-1]:
            current = current.setdefault(key,{})
        current[keys[-1]] = value