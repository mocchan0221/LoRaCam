import cv2
import numpy as np
import tflite_runtime.interpreter as tflite

# COCOデータセットのクラス名
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

class YoloDetector:
    def __init__(self, model_path, num_threads=4, conf_threshold=0.4, nms_threshold=0.45):
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        
        # モデル読み込み
        self.interpreter = tflite.Interpreter(model_path=model_path, num_threads=num_threads)
        self.interpreter.allocate_tensors()
        
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        input_shape = self.input_details[0]['shape'] 
        self.model_input_size = (input_shape[1], input_shape[2]) # (Width, Height)

        # 量子化パラメータの取得
        self.input_dtype = self.input_details[0]['dtype']
        self.input_index = self.input_details[0]['index']
        self.input_scale, self.input_zero_point = self.input_details[0]['quantization']

        self.output_dtype = self.output_details[0]['dtype']
        self.output_index = self.output_details[0]['index']
        self.output_scale, self.output_zero_point = self.output_details[0]['quantization']

    def preprocess(self, image):
        """Letterbox処理と正規化"""
        ih, iw = image.shape[:2]
        w, h = self.model_input_size
        scale = min(w / iw, h / ih)
        nw, nh = int(iw * scale), int(ih * scale)
        image_resized = cv2.resize(image, (nw, nh))
        new_image = np.full((h, w, 3), 0, dtype=np.uint8)
        dx = (w - nw) // 2
        dy = (h - nh) // 2
        new_image[dy:dy+nh, dx:dx+nw, :] = image_resized
        
        # RGB変換
        img_rgb = cv2.cvtColor(new_image, cv2.COLOR_BGR2RGB)
        
        # 型に応じた変換
        if self.input_dtype == np.int8:
            img_norm = img_rgb.astype(np.float32) / 255.0
            img_input = (img_norm / self.input_scale) + self.input_zero_point
            input_data = np.clip(img_input, -128, 127).astype(np.int8)
            input_data = np.expand_dims(input_data, axis=0)
        elif self.input_dtype == np.uint8:
            input_data = np.expand_dims(img_rgb, axis=0).astype(np.uint8)
        else:
            img_norm = img_rgb.astype(np.float32) / 255.0
            input_data = np.expand_dims(img_norm, axis=0)
            
        return input_data, scale, (dx, dy)

    def detect(self, image):
        """推論実行と結果のパース"""
        input_data, scale, pad = self.preprocess(image)
        
        self.interpreter.set_tensor(self.input_index, input_data)
        self.interpreter.invoke()
        
        output_data = self.interpreter.get_tensor(self.output_index)
        output_data = output_data[0].transpose()

        # デオンタイズ（必要な場合）
        if self.output_dtype == np.int8 or self.output_dtype == np.uint8:
            if self.output_scale > 0:
                output_data = (output_data.astype(np.float32) - self.output_zero_point) * self.output_scale

        # 解析ロジック
        boxes_candidate = []
        confidences = []
        class_ids = []

        all_scores = output_data[:, 4:]
        max_scores = np.max(all_scores, axis=1)
        max_indices = np.argmax(all_scores, axis=1)
        
        valid_rows = np.where(max_scores > self.conf_threshold)[0]

        for i in valid_rows:
            score = float(max_scores[i])
            class_id = int(max_indices[i])
            row = output_data[i]
            
            cx = row[0] * self.model_input_size[0]
            cy = row[1] * self.model_input_size[1]
            w = row[2]  * self.model_input_size[0]
            h = row[3]  * self.model_input_size[1]
            
            left = int(cx - w/2)
            top = int(cy - h/2)
            
            boxes_candidate.append([left, top, int(w), int(h)])
            confidences.append(score)
            class_ids.append(class_id)

        indices = cv2.dnn.NMSBoxes(boxes_candidate, confidences, self.conf_threshold, self.nms_threshold)
        
        results = []
        if len(indices) > 0:
            for i in indices:
                idx = i if isinstance(i, (int, np.integer)) else i[0]
                box = self._scale_coords(boxes_candidate[idx], scale, pad)
                results.append({
                    "box": box,
                    "score": confidences[idx],
                    "class_id": class_ids[idx],
                    "class_name": CLASSES[class_ids[idx]]
                })
        return results

    def _scale_coords(self, box, scale, pad):
        dx, dy = pad
        left = int((box[0] - dx) / scale)
        top = int((box[1] - dy) / scale)
        width = int(box[2] / scale)
        height = int(box[3] / scale)
        return [left, top, width, height]

    def draw_results(self, image, results):
        """画像へのバウンディングボックス描画"""
        color = (0, 255, 0)
        for res in results:
            left, top, width, height = res["box"]
            left = max(0, left)
            top = max(0, top)
            
            label = f"{res['class_name']} {res['score']:.2f}"
            cv2.rectangle(image, (left, top), (left + width, top + height), color, 3)
            cv2.putText(image, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        return image