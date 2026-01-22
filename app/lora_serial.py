import serial
import time
import binascii

class LoRaCommunicator:
    def __init__(self, port='/dev/ttyS0', baudrate=9600, timeout=1):
        """
        初期化処理
        :param port: シリアルポート (Pi Zero 2 Wは通常 /dev/ttyS0)
        :param baudrate: A660デフォルトは9600 [cite: 478]
        :param timeout: シリアル読み込みタイムアウト
        """
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.debug = True  # デバッグ表示用フラグ

    def _send_at(self, command, wait_time=0.1):
        """
        ATコマンドを送信し、レスポンスを返す内部メソッド
        コマンド末尾には <CR> (\r) を付与 [cite: 466]
        """
        full_command = command + "\r"
        if self.debug:
            print(f"[Send] {command}")
        
        self.ser.write(full_command.encode('utf-8'))
        time.sleep(wait_time)
        
        response = []
        while self.ser.in_waiting > 0:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    response.append(line)
            except Exception as e:
                print(f"Read Error: {e}")
                
        if self.debug:
            for line in response:
                print(f"[Recv] {line}")
                
        return response

    def connect_network(self, dev_eui, app_eui, app_key, region=3):
        """
        LoRaWANネットワークへの接続 (Join) を行う
        設定: Class A, OTAA
        :param region: 3 = AS923-1-JP (日本) 
        """
        print("--- Configuring LoRa Module ---")
        
        # 1. リセット (念のため) [cite: 670]
        self._send_at("AT+IREBOOT=0", wait_time=2)

        # 2. リージョン設定 (日本: AS923-1-JP) 
        self._send_at(f"AT+RREGION={region}")
        
        # 3. Class A設定 [cite: 568]
        self._send_at("AT+CCLASS=0")
        
        # 4. OTAAモード設定 [cite: 519]
        self._send_at("AT+CJOINMODE=0")

        # 5. キーの設定 [cite: 512, 526, 533]
        if not self._send_at(f"AT+CDEVEUI={dev_eui}"): return False
        if not self._send_at(f"AT+CAPPEUI={app_eui}"): return False
        if not self._send_at(f"AT+CAPPKEY={app_key}"): return False

        # 6. 設定保存 [cite: 613]
        self._send_at("AT+CSAVE")

        # 7. Join開始 (Start, Auto-off, 8s interval, 3 retries) [cite: 626]
        print("--- Starting JOIN Request ---")
        self._send_at("AT+DJOIN=1,0,8,3", wait_time=1)

        # Join完了待ち (ステータス確認ループ)
        # AT+DULSTAT? -> 04: JOIN succeeded, 05: JOIN fails 
        max_retries = 30
        for _ in range(max_retries):
            resp = self._send_at("AT+DULSTAT?", wait_time=1)
            for line in resp:
                if "+DULSTAT:04" in line or "+DULSTAT:03" in line:
                    print(">>> Network Joined Successfully! <<<")
                    return True
                if "+DULSTAT:05" in line:
                    print(">>> Join Failed. Check Keys or Gateway coverage. <<<")
                    return False
            time.sleep(2) # ポーリング間隔
            
        print(">>> Join Timed out <<<")
        return False

    def send_data(self, data_str, confirm=0):
        """
        データを送信する
        :param data_str: 送信する文字列 (自動的にHex変換されます)
        :param confirm: 0=Unconfirmed, 1=Confirmed 
        """
        # 文字列をHex文字列に変換 ("Hello" -> "48656C6C6F")
        hex_payload = binascii.hexlify(data_str.encode('utf-8')).decode('utf-8').upper()
        length = len(hex_payload) // 2
        
        # AT+DTRX=<confirm>,<nbtrials>,<len>,<payload> 
        # 再送回数(nbtrials)はデフォルト2として固定しています
        command = f"AT+DTRX={confirm},2,{length},{hex_payload}"
        
        resp = self._send_at(command, wait_time=2)
        
        # 簡易的な成功判定
        for line in resp:
            if "OK+SENT" in line: # 送信完了通知 
                return True
            if "ERROR" in line:
                return False
        return True

    def receive_data(self):
        """
        受信バッファを確認し、データがあれば返す
        AT+DRX? を使用 
        :return: 受信した文字列 (データがない場合は None)
        """
        resp = self._send_at("AT+DRX?", wait_time=0.2)
        
        # レスポンス例: +DRX=5,48656C6C6F
        for line in resp:
            if line.startswith("+DRX="):
                try:
                    parts = line.split(",")
                    if len(parts) >= 2:
                        length = int(parts[0].split("=")[1])
                        if length > 0:
                            hex_data = parts[1]
                            # Hexを文字列に戻す
                            decoded_str = binascii.unhexlify(hex_data).decode('utf-8', errors='ignore')
                            return decoded_str
                except Exception as e:
                    print(f"Parse Error: {e}")
        return None

    def close(self):
        self.ser.close()