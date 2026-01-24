import time
import datetime
import cv2
import os
import sys
from app import Camera, YoloDetector, LoggerHandler, LoRaCommunicator,ConfigManager, SystemInitializer

MODEL_PATH = "models/yolov8n_full_integer_quant.tflite"

def main():
    print("YOLO Person detection system activated!")

    # 設定の読み込み
    print("Config Loading...")
    config_mgr = ConfigManager()
    config = config_mgr.load()

    if config == None:
        print("Error: Could not load any configuration.")
        sys.exit(1)

    # ネットワーク設定の抽出
    is_latest = config.get("Network",{}).get("IsLatest",1)
    ssid = config.get("Network",{}).get("SSID","SSID")
    password = config.get("Network",{}).get("PASSWORD","PASS")
    hostname = config.get("Network",{}).get("HostName","jkkb.local")
    wifi_enabled = config.get("Network",{}).get("wifi_enabled",0)

    # ネットワーク設定
    if is_latest:
        print("All system setting is latest!")
    else:
        print("New System setting is detected:")
        initializer = SystemInitializer(ssid=ssid, password=password, hostname=hostname,wifi_enabled=wifi_enabled)
        if initializer.execute_all():
            print("New Configuration is successfully applied!")

            if config_mgr.update_status(1):
                print("Status updated. Rebooting system in 3 seconds...")
                time.sleep(5)
                initializer.reboot()
            else:
                print("Failed to update config file.")
                sys.exit(1)
        else:
            print("Errors occurred during system configuration.")

    # カメラ部分の抽出
    camera_focus = config.get("Camera", {}).get("Focus",0.0)
    detect_conf = config.get("Detection",{}).get("CONF_THRESHOLD",0.4)
    interval = config.get("Detection",{}).get("Interval",5)
    print("Loaded Detection Configuration:")
    print(f" - Focus: {camera_focus}")
    print(f" - Conf Threshold: {detect_conf}")
    print(f" - Interval: {interval} sec")

    # LoRa部分の抽出
    DEV_EUI = config.get("LoRa",{}).get("DEVEUI","0000000000000000")
    APP_EUI = config.get("LoRa",{}).get("APPEUI","0000000000000000")
    APP_KEY = config.get("LoRa",{}).get("APPKEY","00000000000000000000000000000000")
    IS_JOINED = config.get("LoRa",{}).get("IsJoined",0)
    print("Loaded LoRa Configuration:")
    print(f" - DEV_EUI: {DEV_EUI}")
    print(f" - APP_EUI: {APP_EUI}")
    print(f" - APP_KEY: {APP_KEY}")    

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

    if IS_JOINED:
        print("Already joined! Skip join process...")
    else:
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
            
            print("Sending data via LoRa")
            send_payload = now_str + " " + str(person_count) 
            
            if lora.send_data(send_payload):
                print("Result: Sent Command Accepted")
                logger.save_lora(now_dt, "SEND", send_payload, "Success")

                print("Checking for response...")
                import time
                time.sleep(2)
                
                # 受信処理
                data = lora.receive_data()
                if data:
                    print(f"Received: {data}")
                    logger.save_lora(datetime.datetime.now(), "RECV", data, "Success")
                else:
                    print("No data received.")
            else:
                print("Result: Send Failed")
                logger.save_lora(now_dt, "SEND", send_payload, "Failed")

            # 指定秒数待機
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        camera.stop()

if __name__ == "__main__":
    main()