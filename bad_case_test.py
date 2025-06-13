import json
import os
import shutil
import urllib.request

# 设置路径
json_path = './results/predictions.json'
visual_dir = './results/visualizations'
bad_case_dir = './bad_case_img'

# 确保输出目录存在
os.makedirs(visual_dir, exist_ok=True)
os.makedirs(bad_case_dir, exist_ok=True)

# 初始化 bad case 计数器
bad_case_count = 0

# 加载 JSON 文件
with open(json_path, 'r', encoding='utf-8') as f:
    predictions = json.load(f)

print("开始处理 bad cases...")

# 处理每一个样本
for item in predictions:
    file_name = item.get('file_name')
    oss_url = item.get('oss_url')
    local_img_path = os.path.join(visual_dir, file_name)

    # 判断是否是 bad case
    # 只要hit_top1, overlap_top1, hit_topk, overlap_topk 中任意一个不为 1，即是 bad case
    if any(item.get(key) != 1 for key in ['hit_top1', 'overlap_top1', 'hit_topk', 'overlap_topk']):
        bad_case_count += 1
        
        # 如果本地图片不存在则下载
        if not os.path.exists(local_img_path):
            try:
                print(f' Downloading image: {file_name} from {oss_url}')
                urllib.request.urlretrieve(oss_url, local_img_path)
            except Exception as e:
                print(f' Failed to download {file_name}: {e}')
                continue

        # 复制到 bad_case_img 文件夹
        try:
            shutil.copy(local_img_path, os.path.join(bad_case_dir, file_name))
            # 打印 bad case 的信息
            print(f"\n--- Bad Case {bad_case_count} ---")
            print(f"File Name: {file_name}")
            print(f"Instruction (Original Query): {item.get('instruction', 'N/A')}")
            print(f"Rewritten Query: {item.get('rewritten_query', 'N/A')}")
            print(f"OSS URL: {oss_url}")

        except Exception as e:
            print(f' Failed to copy {file_name}: {e}')
            continue

print(f"\n处理完成。共识别到并处理 {bad_case_count} 个 bad case。Bad case 图片已保存到 {bad_case_dir}")

