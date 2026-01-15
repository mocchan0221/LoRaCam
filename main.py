import time
import datetime
import cv2
import os
import sys
from app.config_loader import load_config
from app import Camera, YoloDetector, LoggerHandler, LoRaCommunicator

MODEL_PATH = "models/yolov8n_full_integer_quant.tflite"

def main():
    print("YOLO Person detection system activated...")

    # 設定の読み込み
    config = load_config()
    camera_focus = config.get("Camera", {}).get("focus",0.0)
    detect_conf = config.get("Detection",{}).get("CONF_THRESHOLD",0.4)
    interval = config.get("Detection",{}).get("Interval",5)
    print("Loaded Configuration:")
    print(f" - Focus: {camera_focus}")
    print(f" - Conf Threshold: {detect_conf}")
    print(f" - Interval: {interval} sec")

    DEV_EUI = config.get("LoRa",{}).get("DEVEUI","0000000000000000")
    APP_EUI = config.get("LoRa",{}).get("APPEUI","0000000000000000")
    APP_KEY = config.get("LoRa",{}).get("APPKEY","00000000000000000000000000000000")

    print(f" - DEV_EUI: {DEV_EUI}")
    print(f" - APP_EUI: {APP_EUI}")
    print(f" - APP_KEY: {APP_KEY}")

    # ディレクトリ作成
    save_image_dir = "data/images"
    os.makedirs(save_image_dir, exist_ok=True)

    # クラス初期化
    camera = Camera(width=1280, height=720, focus_val=camera_focus)
    detector = YoloDetector(model_path=MODEL_PATH, conf_threshold=detect_conf)
    logger = LoggerHandler(log_dir="data/logs")

    # LoRa joinプロセス
    print("Start LoRa connection process!")
    print("opening serial port...")
    try:
        lora = LoRaCommunicator(port='/dev/ttyS0')
        print("Serial port opened successfully.")
    except Exception as e:
        print(f"Failed to open serial port: {e}")
        sys.exit(1)
    
    print(f"Joining with DevEUI: {DEV_EUI} ...")
    if lora.connect_network(DEV_EUI, APP_EUI, APP_KEY):
        print("Result: Success!")
    else:
        print("Result: Failed.")
        sys.exit(1)


    print("Start monitoring loop...")

    try:
        while True:
            now_dt = datetime.datetime.now()

            # 撮影・検出・保存
            frame = camera.capture()
            results = detector.detect(frame)
            person_count = logger.save(now_dt, results)
            result_img = detector.draw_results(frame.copy(), results)
            now_str = now_dt.strftime('%Y-%m-%d %H:%M:%S')
            cv2.putText(result_img, now_str, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            save_path = os.path.join("data/images", "latest_result.jpg")
            cv2.imwrite(save_path, result_img)
            print(f"[{now_str}] Count(Person): {person_count} | Saved.")
            
            #LoRa送信
            print("Sending data via LoRa")
            if lora.send_data(str(person_count)):
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

            # 指定秒数待機
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        camera.stop()

if __name__ == "__main__":
    main()