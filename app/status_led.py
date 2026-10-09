import os
from gpiozero import LED

# 基板上の配線 (pcb/LoRaCam.kicad_sch)。scripts/led_error.sh と合わせること
GREEN_PIN = 17  # LED1 (D1), ヘッダー11番ピン
RED_PIN = 27    # LED2 (D2), ヘッダー13番ピン

# 異常終了時に scripts/led_error.sh が作成する。/run は再起動で消える
ERROR_FLAG = "/run/loracam-error"

class StatusLED:
    """
    動作状態表示用LED
      初期化中     : 緑点滅
      正常動作中   : 緑点灯
      前回異常終了 : 赤点灯 (正常動作に入るまで維持)
    異常終了・フリーズ時の赤点灯は systemd 側 (ExecStopPost, WatchdogSec) が担当する
    LEDの制御に失敗しても本体の動作は止めない
    """
    def __init__(self):
        self.green = None
        self.red = None
        try:
            self.green = LED(GREEN_PIN)
            self.red = LED(RED_PIN, initial_value=os.path.exists(ERROR_FLAG))
        except Exception as e:
            print(f"[Warning] Status LED disabled: {e}")

    def initializing(self):
        if self.green:
            self.green.blink(on_time=0.5, off_time=0.5)

    def running(self):
        if self.green:
            self.green.on()
        if self.red:
            self.red.off()
        try:
            os.remove(ERROR_FLAG)
        except FileNotFoundError:
            pass

    def close(self):
        for led in (self.green, self.red):
            if led:
                led.close()
