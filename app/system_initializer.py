import subprocess
import os
import time

class SystemInitializer:
    def __init__(self, ssid: str, password: str, hostname: str, wifi_enabled: int):
        self.ssid = ssid
        self.password = password
        self.hostname = hostname.strip()
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
        current_hostname = os.uname().nodename
        if current_hostname == self.hostname:
            print("Hostname is already set. Skippping")
            return True
        
        hosts_path = "/etc/hosts"
        try:
            with open(hosts_path, 'r') as f:
                lines = f.readlines()
                new_lines = []
                replaced = False
                for line in lines:
                    if line.strip().startswith("127.0.1.1"):
                        new_lines.append(f"127.0.1.1\t{self.hostname}\n")
                        replaced = True
                    else:
                        new_lines.append(line)
                if not replaced:
                    new_lines.append(f"127.0.1.1\t{self.hostname}\n")
            
            with open(hosts_path, 'w') as f:
                f.writelines(new_lines)
            os.sync()
            print("/etc/hosts/ updated.")
        
        except Exception as e:
            print(f"Error Failed to write /etc/hosts: {e}")
            return False
        
        if not self._run_command(["hostnamectl", "set-hostname", self.hostname]):
            print("Error hostnamectl failed.")
            return False

        print("Restarting avahi-daemon to apply .local name...")
        self._run_command(["systemctl","restart","avahi-daemon"])
        return True

    def execute_all(self) -> bool:
        if os.geteuid() != 0:
            print("Error Root privileges required")
            return False
        host_res = self.configure_hostname()
        wifi_res = self.configure_wifi()

        return wifi_res and host_res

    def reboot(self):
        print("[*] Rebooting system...")
        time.sleep(1)
        subprocess.run(["reboot"])