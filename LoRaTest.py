from app import LoRaCommunicator,ConfigManager
import time
import sys


def print_help():
    print("\n--- Available Commands ---")
    print("  join          : ネットワークへ接続 (Connect Network)")
    print("  send <text>   : テキストデータを送信 (例: send Hello)")
    print("  recv          : 受信データを確認 (Check Rx buffer)")
    print("  at <command>  : 生のATコマンドを送信 (例: at AT+CGMR?)")
    print("  help          : コマンド一覧を表示")
    print("  exit          : 終了")
    print("--------------------------")

def main():
    print("welcome to LoRa test program!")
    config_mgr = ConfigManager()
    config = config_mgr.load()

    DEV_EUI = config.get("LoRa",{}).get("DEVEUI","0000000000000000")
    APP_EUI = config.get("LoRa",{}).get("APPEUI","0000000000000000")
    APP_KEY = config.get("LoRa",{}).get("APPKEY","00000000000000000000000000000000")

    print("Config is set as below...")
    print(f" - DEV_EUI: {DEV_EUI}")
    print(f" - APP_EUI: {APP_EUI}")
    print(f" - APP_KEY: {APP_KEY}")

    # インスタンス作成
    try:
        lora = LoRaCommunicator(port='/dev/ttyS0')
        print("Serial port opened successfully.")
    except Exception as e:
        print(f"Failed to open serial port: {e}")
        sys.exit(1)

    print_help()

    try:
        while True:
            # ユーザー入力待機
            try:
                user_input = input("\nLoRa> ").strip()
            except EOFError:
                break
            
            if not user_input:
                continue

            # 入力をコマンドと引数に分割
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            # --- コマンド処理 ---
            if cmd == "exit":
                print("Bye!")
                break

            elif cmd == "help":
                print_help()

            elif cmd == "join":
                print(f"Joining with DevEUI: {DEV_EUI} ...")
                if lora.connect_network(DEV_EUI, APP_EUI, APP_KEY):
                    print("Result: Success!")
                else:
                    print("Result: Failed.")

            elif cmd == "send":
                if not args:
                    print("Error: 送信テキストを指定してください (例: send Hello)")
                    continue
                print(f"Sending: '{args}'")
                if lora.send_data(args):
                    print("Result: Sent Command Accepted")
                    # 送信直後に自動で受信チェックも行うと便利
                    print("Checking for response...")
                    # Class Aの受信ウィンドウ待ち (少し待ってから確認)
                    import time
                    time.sleep(2)
                    data = lora.receive_data()
                    if data:
                        print(f"Received: {data}")
                    else:
                        print("No data received.")
                else:
                    print("Result: Send Failed")

            elif cmd == "recv":
                data = lora.receive_data()
                if data:
                    print(f"Received Data: {data}")
                else:
                    print("Buffer empty.")

            elif cmd == "at":
                # デバッグ用: 直接ATコマンドを送る
                if not args:
                    print("Error: ATコマンドを指定してください (例: at AT+DULSTAT?)")
                    continue
                # LoRa_Serialの内部メソッド _send_at を利用
                resp = lora._send_at(args, wait_time=0.5)
                # 結果は _send_at 内でprintされる(debug=Trueなら)が、ここでも確認
                print("--- Raw Response ---")
                for line in resp:
                    print(line)

            else:
                print(f"Unknown command: '{cmd}'. Type 'help' for list.")

    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        lora.close()
        print("Serial closed.")

if __name__ == "__main__":
    main()