import os
import socket

def notify(state):
    """
    systemd にサービスの状態を通知する (sd_notify 相当)
    例: "READY=1" (起動完了), "WATCHDOG=1" (生存通知)
    systemd 外で実行した場合は何もしない
    """
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr:
        return False
    if addr.startswith("@"):
        addr = "\0" + addr[1:]
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
            s.connect(addr)
            s.sendall(state.encode())
        return True
    except OSError as e:
        print(f"[Warning] systemd notify failed: {e}")
        return False
