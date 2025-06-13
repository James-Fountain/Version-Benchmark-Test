from screenSpot_v2 import get_metric as calculate_metric
import json
import os

def generate_metric(pred_path, metric_path):
    # 为了计算评估指标，需要重新读取完整的 predictions.json 文件
    with open(pred_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    metric_info = calculate_metric(results)
    with open(metric_path, "w", encoding="utf-8") as f:
        f.write(metric_info)
    print(f"评估指标已保存至：{metric_path}")

if __name__ == "__main__":
    # 确保 results 目录存在
    results_dir = "./results"
    os.makedirs(results_dir, exist_ok=True)

    pred_file_path = os.path.join(results_dir, "predictions.json")
    metric_file_path = os.path.join(results_dir, "metrics.txt")

    generate_metric(pred_file_path, metric_file_path)

