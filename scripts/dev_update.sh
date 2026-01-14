#!/bin/bash

set -e

PROJECT_DIR="/home/jkkb/LoRaCam"
cd $PROJECT_DIR

echo "LoRaCam自動更新スクリプトへようこそ"

echo "最新コードの取得中"
git pull origin main

echo "ライブラリの更新中"
$PROJECT_DIR/.venv/bin/pip install -r requirements.txt

echo "サービスファイルの更新中"
sudo cp $PROJECT_DIR/services/LoRaCam.service /etc/systemd/system
sudo cp $PROJECT_DIR/services/WebMonitor.service /etc/systemd/system

echo "サービスを再起動中"
sudo systemctl daemon-reload
sudo systemctl restart LoRaCam.service
sudo systemctl restart WebMonitor.service

echo "更新が完了しました"
sudo systemctl status LoRaCam.service --no-pager
sudo systemctl status WebMonitor.service --no-pager
