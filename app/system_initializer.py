import subprocess
import os
import time

class SystemInitializer:
    def __init__(self, ssid: str, password: str, hostname: str, wifi_enabled: int):
        self.ssid = ssid
        self.password = password
        self.hostname = hostname
        self.wifi_enabled = wifi_enabled

    def _run_command(self, command: list) -> bool:
        try:
            subprocess.run(
                command, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"[Error] Cmd: {' '.join(command)}\nDetails: {e.stderr.strip()}")
            return False

    def configure_wifi(self) -> bool:
        print(f"Configuring Wi-Fi (Enabled: {self.wifi_enabled})...")

        if self.wifi_enabled == 0:
            print("  - Disabling Wi-Fi radio...")
            if self._run_command(["nmcli", "radio", "wifi", "off"]):
                print("  -> Wi-Fi turned OFF.")
                return True
            else:
                return False
        print("  - Enabling Wi-Fi radio...")
        if not self._run_command(["nmcli", "radio", "wifi", "on"]):
            return False
        
        time.sleep(2)

        print(f"  - Connecting to SSID: {self.ssid}")
        subprocess.run(["nmcli", "connection", "delete", self.ssid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cmd = ["nmcli", "device", "wifi", "connect", self.ssid, "password", self.password]
        if self._run_command(cmd):
            print("  -> Wi-Fi Connected.")
            return True
        else:
            return False

    def configure_hostname(self) -> bool:
        print(f"[*] Setting hostname to: {self.hostname}...")
        if not self._run_command(["hostnamectl", "set-hostname", self.hostname]):
            return False
        
        hosts_path = "/etc/hosts"
        try:
            with open(hosts_path, 'r') as f:
                lines = f.readlines()
            with open(hosts_path, 'w') as f:
                for line in lines:
                    if line.strip().startswith("127.0.1.1"):
                        f.write(f"127.0.1.1\t{self.hostname}\n")
                    else:
                        f.write(line)
            return True
        except Exception as e:
            print(f"[Error] /etc/hosts update failed: {e}")
            return False

    def execute_all(self) -> bool:
        wifi_result = self.configure_wifi()
        hostname_result = self.configure_hostname()

        return wifi_result and hostname_result

    def reboot(self):
        print("[*] Rebooting system...")
        subprocess.run(["reboot"])