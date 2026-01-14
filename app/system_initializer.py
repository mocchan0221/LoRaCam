# システム設定変更用プログラム

import subprocess
import time

def setup_wifi(ssid, password):
    #Wi-Fi設定プログラム

    print(f"Setting up Wi-Fi: {ssid}")
    cmd = [
        "nmcli", "device", "wifi", "connect", ssid, "password", password
    ]
    
    try:
        subprocess.run(cmd, check=True, timeout=30)
        print("Wi-Fi Connected.")
        time.sleep(5) 
    except subprocess.CalledProcessError as e:
        print(f"Wi-Fi Connection Failed: {e}")
    except Exception as e:
        print(f"Unknown Error in Wi-Fi setup: {e}")