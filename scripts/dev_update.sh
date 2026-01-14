#!/bin/bash

set -e

PROJECT_DIR = "/home/jkkb/LoRaCam"
cd $PROJECT_DIR

echo "LoRaCam自動更新スクリプトへようこそ"

echo "最新コードの取得中"
git pull origin main

echo "ライブラリの更新中"
$PROJECT_DIR/.venv/bin/pip install -r requirements.txt

echo "サービスファイルの更新中"
sudo cp $PROJECT_DIR/services/LoRaCam.service /etc/systemd/system

echo "サービスを再起動中"
sudo sytemctl daemon-reload
sudo systemctl restart LoRaCam.service

echo "更新が完了しました"
sudo systemctl status LoRaCam.service --no-pager
