import csv
import os

class LoggerHandler:
    def __init__(self, log_dir="data/logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.file_all = os.path.join(self.log_dir, "logAll.csv")
        self.file_person = os.path.join(self.log_dir, "logPerson.csv")

    def save(self, dt, results):
        """
        検出結果を受け取ってCSVに保存する
        results: detector.detect() の戻り値リスト
        """
        # 集計
        counts = {}
        for res in results:
            cname = res['class_name']
            counts[cname] = counts.get(cname, 0) + 1

        # 1. logPerson.csv (Personのみ)
        person_count = counts.get("person", 0)
        self._write_csv(self.file_person, dt, "person", person_count)

        # 2. logAll.csv (全クラス)
        if len(counts) > 0:
            for cname, count in counts.items():
                self._write_csv(self.file_all, dt, cname, count)
        
        return person_count

    def _write_csv(self, filepath, dt, class_name, count):
        file_exists = os.path.isfile(filepath)
        date_str = dt.strftime('%Y-%m-%d')
        time_str = dt.strftime('%H:%M:%S')
        
        with open(filepath, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Date', 'Time', 'Class', 'Count'])
            writer.writerow([date_str, time_str, class_name, count])