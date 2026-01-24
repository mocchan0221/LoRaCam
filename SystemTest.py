import time
import sys
from app import ConfigManager, SystemInitializer


def main():
    print("This is test for Config Manager and System Initializer")

    # 設定の読み込み
    print("Config Loading...")
    config_mgr = ConfigManager()
    config = config_mgr.load()

    if config == None:
        print("Error: Could not load any configuration.")
        sys.exit(1)

    # ネットワーク設定の抽出
    is_latest = config.get("Network",{}).get("IsLatest",1)
    ssid = config.get("Network",{}).get("SSID","SSID")
    password = config.get("Network",{}).get("PASSWORD","PASS")
    hostname = config.get("Network",{}).get("HostName","jkkb.local")
    wifi_enabled = config.get("Network",{}).get("wifi_enabled",0)

    print("Configuration is loaded:")
    print(f" - is_latest: {is_latest}")
    print(f" - ssid: {ssid}")
    print(f" - password: {password}")
    print(f" - hostname: {hostname}")
    print(f" - wifi_enabled: {wifi_enabled}")

    # ネットワーク設定
    if is_latest:
        print("All system setting is latest! End this program")
    else:
        print("New System setting is detected:")
        initializer = SystemInitializer(ssid=ssid, password=password, hostname=hostname,wifi_enabled=wifi_enabled)
        if initializer.execute_all():
            print("New Configuration is successfully applied!")

            if config_mgr.update_status(1):
                print("Status updated. Rebooting system in 3 seconds...")
                time.sleep(5)
                initializer.reboot()
            else:
                print("Failed to update config file.")
                sys.exit(1)
        else:
            print("Errors occurred during system configuration.")


if __name__ == "__main__":
    main()