import cv2
import numpy as np
import tflite_runtime.interpreter as tflite
import time
import datetime
import csv
import os
from picamera2 import Picamera2, controls

# 各種設定
MODEL_PATH = "models/yolov8n_full_integer_quant.tflite"
CONF_THRESHOLD = 0.4
NMS_THRESHOLD = 0.45
NUM_THREADS = 4
INTERVAL_SECONDS = 5

# ログ設定
LOG_DIR = "log"
LOG_FILE_ALL = os.path.join(LOG_DIR, "logAll.csv")
LOG_FILE_PERSON = os.path.join(LOG_DIR, "logPerson.csv")
os.makedirs(LOG_DIR, exist_ok=True)

# COCOデータセットのクラス名（YOLO標準）
CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush"
]

# マニュアルフォーカス値
FOCUS_VAL = 0.0

# カメラ解像度設定
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

# モデル読み込み
interpreter = tflite.Interpreter(model_path=MODEL_PATH, num_threads=NUM_THREADS)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
input_shape = input_details[0]['shape'] 
MODEL_INPUT_SIZE = (input_shape[1], input_shape[2])

input_dtype = input_details[0]['dtype']
input_index = input_details[0]['index']
input_scale, input_zero_point = input_details[0]['quantization']

output_dtype = output_details[0]['dtype']
output_index = output_details[0]['index']
output_scale, output_zero_point = output_details[0]['quantization']

# カメラ初期化
picam2 = Picamera2()
config = picam2.create_video_configuration(main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT), "format": "BGR888"})
picam2.configure(config)
picam2.start()

# フォーカス固定
picam2.set_controls({
    "AfMode": 0,
    "LensPosition": FOCUS_VAL
})
print(f"Camera initialized with Manual Focus: {FOCUS_VAL}")

# 関数群
def letterbox_image(image, target_size):
    ih, iw = image.shape[:2]
    w, h = target_size
    scale = min(w / iw, h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    image_resized = cv2.resize(image, (nw, nh))
    new_image = np.full((h, w, 3), 0, dtype=np.uint8)
    dx = (w - nw) // 2
    dy = (h - nh) // 2
    new_image[dy:dy+nh, dx:dx+nw, :] = image_resized
    return new_image, scale, (dx, dy)

def scale_coords(box, scale, pad):
    dx, dy = pad
    left = int((box[0] - dx) / scale)
    top = int((box[1] - dy) / scale)
    width = int(box[2] / scale)
    height = int(box[3] / scale)
    return [left, top, width, height]

def draw_boxes(image, boxes, confs, class_ids):
    # クラスごとに色を変えるなどはせず、一律緑で描画（必要なら変更可）
    color = (0, 255, 0)
    for i, box in enumerate(boxes):
        left, top, width, height = box
        left = max(0, left)
        top = max(0, top)
        
        class_name = CLASSES[class_ids[i]]
        cv2.rectangle(image, (left, top), (left + width, top + height), color, 3)
        
        # 表示テキスト: "person 0.85"
        label = f"{class_name} {confs[i]:.2f}"
        cv2.putText(image, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return image

def save_to_csv(filepath, now_dt, class_name, count):
    """
    CSVにデータを追記する関数
    Format: Date, Time, Class, Count
    """
    file_exists = os.path.isfile(filepath)
    
    date_str = now_dt.strftime('%Y-%m-%d')
    time_str = now_dt.strftime('%H:%M:%S')
    
    with open(filepath, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Date', 'Time', 'Class', 'Count'])
        
        writer.writerow([date_str, time_str, class_name, count])

def detect():
    print(f"Start monitoring loop (Focus: {FOCUS_VAL})...")
    
    try:
        while True:
            start_time = time.time()
            
            # 画像取得・前処理
            frame = picam2.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ai_input_img, scale, pad = letterbox_image(frame, MODEL_INPUT_SIZE)
            img_rgb = cv2.cvtColor(ai_input_img, cv2.COLOR_BGR2RGB)

            if input_dtype == np.int8:
                img_norm = img_rgb.astype(np.float32) / 255.0
                img_input = (img_norm / input_scale) + input_zero_point
                input_data = np.clip(img_input, -128, 127).astype(np.int8)
                input_data = np.expand_dims(input_data, axis=0)
            elif input_dtype == np.uint8:
                input_data = np.expand_dims(img_rgb, axis=0).astype(np.uint8)
            else:
                img_norm = img_rgb.astype(np.float32) / 255.0
                input_data = np.expand_dims(img_norm, axis=0)

            # 推論実行
            interpreter.set_tensor(input_index, input_data)
            interpreter.invoke()

            # 出力データ取得
            output_data = interpreter.get_tensor(output_index)
            output_data = output_data[0].transpose() # (8400, 84)

            if output_dtype == np.int8 or output_dtype == np.uint8:
                if output_scale > 0:
                    output_data = (output_data.astype(np.float32) - output_zero_point) * output_scale

            boxes_candidate = []
            confidences = []
            class_ids = []
            
            # --- 解析ロジック変更点 ---
            # output_dataの構造: [cx, cy, w, h, score_class0, score_class1, ..., score_class79]
            # 4列目以降(クラススコア)から最大値とそのインデックスを取得
            
            # numpyを使って一括処理（高速化）
            all_scores = output_data[:, 4:] # 全クラスのスコア部分
            max_scores = np.max(all_scores, axis=1) # 各行の最大スコア
            max_indices = np.argmax(all_scores, axis=1) # その最大スコアを持つクラスID
            
            # 閾値を超えるものだけ抽出
            valid_rows = np.where(max_scores > CONF_THRESHOLD)[0]

            for i in valid_rows:
                score = float(max_scores[i])
                class_id = int(max_indices[i])
                row = output_data[i]
                
                cx = row[0] * MODEL_INPUT_SIZE[0]
                cy = row[1] * MODEL_INPUT_SIZE[1]
                w = row[2]  * MODEL_INPUT_SIZE[0]
                h = row[3]  * MODEL_INPUT_SIZE[1]
                
                left = int(cx - w/2)
                top = int(cy - h/2)
                
                boxes_candidate.append([left, top, int(w), int(h)])
                confidences.append(score)
                class_ids.append(class_id)

            # NMS実行
            indices = cv2.dnn.NMSBoxes(boxes_candidate, confidences, CONF_THRESHOLD, NMS_THRESHOLD)
            
            final_boxes = []
            final_scores = []
            final_class_ids = []
            
            if len(indices) > 0:
                for i in indices:
                    idx = i if isinstance(i, (int, np.integer)) else i[0]
                    scaled_box = scale_coords(boxes_candidate[idx], scale, pad)
                    
                    final_boxes.append(scaled_box)
                    final_scores.append(confidences[idx])
                    final_class_ids.append(class_ids[idx])
            
            # --- 集計とログ保存 ---
            now_dt = datetime.datetime.now()
            
            # クラスごとのカウントを集計するための辞書
            # 例: {'person': 3, 'car': 1}
            counts = {}
            for cid in final_class_ids:
                cname = CLASSES[cid]
                counts[cname] = counts.get(cname, 0) + 1

            # 1. logPerson.csv には "person" の数だけ保存（いなければ0）
            person_count = counts.get("person", 0)
            save_to_csv(LOG_FILE_PERSON, now_dt, "person", person_count)

            # 2. logAll.csv には検出された全クラスを保存
            # 何も検出されなかった場合、記録しない（あるいは None 0 を記録するかはお好みで。今回は記録しない）
            if len(counts) > 0:
                for cname, count in counts.items():
                    save_to_csv(LOG_FILE_ALL, now_dt, cname, count)
            else:
                # 何も検知しなかった行も残したい場合はここを有効化
                pass

            # --- 描画と表示 ---
            result_img = draw_boxes(frame.copy(), final_boxes, final_scores, final_class_ids)
            now_str = now_dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # 画像へのタイムスタンプ
            cv2.putText(result_img, now_str, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.imwrite("images/latest_result.jpg", result_img)
            
            # ターミナル表示（要望通り Person の数だけ表示）
            print(f"[{now_str}] Count(Person): {person_count} | Saved.")
            
            time.sleep(INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        picam2.stop()

if __name__ == "__main__":
    detect()
