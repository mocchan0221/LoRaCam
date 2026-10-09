#!/bin/bash
# LoRaCam.service の停止時に systemd (ExecStopPost) から呼ばれる
#   異常終了 (エラー終了・クラッシュ・watchdog によるフリーズ検出) なら赤LEDを点灯し、
#   次回起動時に main.py が赤を維持できるようフラグを残す
#   正常停止 (systemctl stop / restart) なら両方消灯する
# ピン番号は app/status_led.py と合わせること

GREEN_PIN=17
RED_PIN=27
ERROR_FLAG=/run/loracam-error

pinctrl set $GREEN_PIN op dl

if [[ "${SERVICE_RESULT:-success}" != "success" ]]; then
    pinctrl set $RED_PIN op dh
    echo "$(date '+%F %T') ${SERVICE_RESULT} ${EXIT_CODE:-} ${EXIT_STATUS:-}" > "$ERROR_FLAG"
else
    pinctrl set $RED_PIN op dl
    rm -f "$ERROR_FLAG"
fi
