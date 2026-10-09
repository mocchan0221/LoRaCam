# LoRaCam
AI camera via LoRa on Raspberry Pi

Raspberry Pi + カメラで YOLOv8n (TFLite) による人数カウントを行い、結果を CSV に記録しつつ LoRaWAN で送信するデバイス。

## 動作環境
- Raspberry Pi Zero 2 W / Raspberry Pi OS Bookworm (Python 3.11)
- Camera Module 3 (imx708)
- LoRa モジュール A660-900T22 (UART `/dev/ttyS0`, 9600bps) — AS923-1 (日本), OTAA, Class A

## ディレクトリ構成
| パス | 内容 |
| --- | --- |
| `main.py` | エントリポイント (設定読込 → Wi-Fi/ホスト名設定 → LoRa Join → 撮影・検出・送信ループ) |
| `app/` | 各種機能 (カメラ, 検出器, ログ, LoRa通信, 設定, システム初期化) |
| `models/` | YOLO モデル置き場 (git管理外) |
| `data/images`, `data/logs` | 最新の検出画像・CSVログ (git管理外) |
| `services/` | systemd サービス定義 |
| `scripts/dev_update.sh` | 開発機用ワンクリック更新スクリプト |
| `LoRaTest.py`, `SystemTest.py` | LoRa 通信 / システム設定の単体テスト |
| `pcb/` | 基板データ (KiCad) |

## セットアップ (開発機)
サービス定義と更新スクリプトはユーザー `jkkb`、パス `/home/jkkb/LoRaCam` 前提。

1. `sudo raspi-config` → Interface Options → Serial Port で「Login shell: No」「Serial port hardware: Yes」にして再起動
2. リポジトリを取得して仮想環境を作成
   ```bash
   cd ~ && git clone https://github.com/mocchan0221/LoRaCam.git && cd LoRaCam
   sudo apt install -y python3-picamera2 python3-opencv
   python3 -m venv --system-site-packages .venv   # apt の picamera2 を venv から使うため
   .venv/bin/pip install -r requirements.txt
   ```
   - tflite-runtime は numpy 2.x では動かないため `numpy<2` (requirements では 1.26.4) を使う
   - シリアル通信は `pyserial`。`serial` パッケージを入れると `module 'serial' has no attribute 'Serial'` になる
3. モデルを用意 (PC 側で変換して `models/` にコピー)
   ```bash
   pip install ultralytics
   yolo export model=yolov8n.pt format=tflite int8
   # → yolov8n_saved_model/yolov8n_full_integer_quant.tflite を models/ へ
   ```
4. 設定ファイルを配置: `config_template.json` を `/boot/firmware/config.json` にコピーして編集 (下記)
5. サービス登録
   ```bash
   sudo cp services/*.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now LoRaCam.service WebMonitor.service
   ```

## 設定 (`/boot/firmware/config.json`)
| キー | 内容 |
| --- | --- |
| `LoRa.DEVEUI` / `APPEUI` / `APPKEY` | OTAA 用のキー |
| `LoRa.IsJoined` | 1 なら起動時の Join をスキップ |
| `Camera.Focus` | マニュアルフォーカス値 (LensPosition, 0.0 = 無限遠) |
| `Network.wifi_enabled` | 0: Wi-Fi OFF / 1: Wi-Fi ON (`SSID`, `PASSWORD` に接続) |
| `Network.HostName` | ホスト名 (`.local` は付けない。例: `jkkb1` → `jkkb1.local` でアクセス) |
| `Network.IsLatest` | 0 にすると次回起動時に Wi-Fi・ホスト名を適用し、1 に書き換えて再起動 |
| `Detection.Interval` | 検出・送信の間隔 [秒] |
| `Detection.CONF_THRESHOLD` | 検出の信頼度しきい値 |

## 動作確認
```bash
journalctl -u LoRaCam.service -f          # 本体のログ
sudo .venv/bin/python LoRaTest.py         # 対話式 LoRa テスト (join / send / recv / at)
sudo .venv/bin/python SystemTest.py       # Wi-Fi・ホスト名設定のテスト (IsLatest=0 のとき再起動する)
```
LoRaTest を使う前に `sudo systemctl stop LoRaCam.service` でシリアルポートを空けておく。

出力:
- `data/logs/logPerson.csv` (人数), `logAll.csv` (全クラス), `logLoRa.csv` (送受信履歴)
- `data/images/latest_result.jpg` (最新の検出画像)
- WebMonitor により `http://<ホスト名>.local:8000/data/` から閲覧可能
- LoRa 送信ペイロード: `"YYYY-mm-dd HH:MM:SS <人数>"` の ASCII 文字列

## 開発フロー
PC で編集して push → 開発機で `bash scripts/dev_update.sh` (pull・pip 更新・サービス更新・再起動を一括実行)。

## デバイスの複製
1. 開発機の SD カードを Win32 Disk Imager でイメージ化 (必要なら WSL2/Linux の pishrink で圧縮)
2. Raspberry Pi Imager 等で新しい SD カードに書き込み
3. PC から bootfs パーティションの `config.json` を個体ごとに編集 (キー、ホスト名など。`IsLatest: 0`, `IsJoined: 0`)
4. 電源投入で初回にネットワーク設定を適用して再起動し、以降は自動で動作開始
