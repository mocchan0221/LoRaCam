import time
import datetime
import cv2
import os
from app import load_config
from app import Camera, YoloDetector, LoggerHandler

MODEL_PATH = "models/yolov8n_full_integer_quant.tflite"

def main():
    print("YOLO Person detection system activated...")

    # 設定の読み込み
    config = load_config()
    camera_focus = config.get("Camera", {}).get("focus",0.0)
    detect_conf = config.get("Detection",{}).get("CONF_THRESHOLD",0.4)
    interval = config.get("Detection",{}).get("Interval",5)
    print(f"Loaded Configuration:")
    print(f" - Focus: {camera_focus}")
    print(f" - Conf Threshold: {detect_conf}")
    print(f" - Interval: {interval} sec")

    # クラス初期化
    camera = Camera(width=1280, height=720, focus_val=camera_focus)
    detector = YoloDetector(model_path=MODEL_PATH, conf_threshold=detect_conf)
    logger = LoggerHandler(log_dir="data/logs")

    print("Start monitoring loop...")

    try:
        while True:
            start_time = time.time()
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
            
            # 指定秒数待機
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        camera.stop()

if __name__ == "__main__":
    main()