import json
import os
import shutil
import urllib.request
import csv # 导入 csv 模块
from PIL import Image, ImageDraw # 图片处理所需库

# --- 辅助函数 (从 run_benchmark.py 复制并修改) ---
def normalize_bbox(bbox_x1y1x2y2, img_width, img_height):
    """将边界框坐标归一化到0-1之间。如果坐标已经归一化，则直接返回；否则，将其除以图像宽度和高度进行归一化。"""
    x1, y1, x2, y2 = bbox_x1y1x2y2
    if (0 <= x1 <= 1) and (0 <= y1 <= 1) and (0 <= x2 <= 1) and (0 <= y2 <= 1):
        return bbox_x1y1x2y2
    else:
        x1 = x1 / img_width
        y1 = y1 / img_height
        x2 = x2 / img_width
        y2 = y2 / img_height
        return x1, y1, x2, y2

def draw_bbox(image, bbox, color="red", width=2):
    """在图像上绘制边界框。此函数会将归一化的边界框坐标转换为像素坐标，并在图像上绘制矩形。"""
    draw = ImageDraw.Draw(image)
    # 确保边界框坐标在图像范围内且顺序正确
    x1, y1, x2, y2 = bbox
    # 将归一化坐标转换为像素坐标
    img_width, img_height = image.size
    x1 = max(0, x1 * img_width)
    y1 = max(0, y1 * img_height)
    x2 = min(img_width, x2 * img_width)
    y2 = min(img_height, y2 * img_height)
    draw.rectangle([x1, y1, x2, y2], outline=color, width=width)
    return image
# --- 辅助函数结束 ---

# 设置路径
json_path = './results/predictions.json'
visual_dir = './results/visualizations' # 用于存放原始/下载图片的目录
bad_case_img_dir = './bad_case_img'    # 用于存放处理后的 bad case 图片的目录

# 确保输出目录存在
os.makedirs(visual_dir, exist_ok=True)
os.makedirs(bad_case_img_dir, exist_ok=True)

print("正在加载 ScreenSpot_v2 测试集以获取原始图片...")

# 加载 JSON 文件
if not os.path.exists(json_path):
    print(f"错误：预测文件未找到，路径为 {json_path}")
    exit() # 如果预测文件未找到，则退出

try:
    with open(json_path, 'r', encoding='utf-8') as f:
        predictions = json.load(f)
except json.JSONDecodeError:
    print(f"错误：无法解析 JSON 文件 {json_path}，请检查文件格式。")
    exit()

print("开始处理 bad cases 并收集信息...")

bad_case_count = 0
bad_cases_output_data = [] # 用于收集 bad case 的关键信息，以便写入CSV表格

# 处理每一个样本
for index, item in enumerate(predictions):
    file_name = item.get('file_name')
    instruction = item.get('instruction', 'N/A')
    rewritten_query = item.get('rewritten_query', 'N/A')
    oss_url = item.get('oss_url')
    pred_bbox = item.get('bbox', []) # 预测边界框
    gt_bbox = item.get('gt_bbox', []) # 真实边界框

    # 判断是否是 bad case (只要hit_top1, overlap_top1, hit_topk, overlap_topk 中任意一个不为 1，即是 bad case)
    if not (item.get('hit_top1') == 1 and item.get('overlap_top1') == 1 and \
            item.get('hit_topk') == 1 and item.get('overlap_topk') == 1):
        
        bad_case_count += 1
        # 创建一个唯一的图片文件名，以避免覆盖
        unique_file_name = f"{index}_{file_name}"
        
        # 获取原始图像：尝试从 visual_dir 加载，如果不存在则从 OSS URL 下载
        local_image_path_in_visuals = os.path.join(visual_dir, file_name)
        original_img = None
        if os.path.exists(local_image_path_in_visuals):
            try:
                original_img = Image.open(local_image_path_in_visuals)
                print(f'✅ 从本地加载图像: {file_name}')
            except Exception as e:
                print(f'❌ 无法打开本地图像 {file_name}: {e}. 尝试从 OSS 下载。')
        
        if not original_img and oss_url:
            try:
                print(f'📥 正在下载图像: {file_name} 从 {oss_url}')
                urllib.request.urlretrieve(oss_url, local_image_path_in_visuals)
                original_img = Image.open(local_image_path_in_visuals)
                print(f'✅ 图像下载并加载成功: {file_name}')
            except Exception as e:
                print(f'❌ 无法从 {oss_url} 下载或打开 {file_name}: {e}')
                continue # 如果无法获取图像，则跳过此 bad case
        elif not original_img and not oss_url:
            print(f"警告：文件 {file_name} 既没有本地图像也没有OSS URL。跳过。")
            continue

        if not original_img: # 如果图像仍然无法加载
            print(f"错误：无法获取 {file_name} 的图像。跳过该 bad case。")
            continue
        
        # 复制一份图片用于绘制
        processed_img = original_img.copy()

        # 绘制边界框
        # 真实框 gt_bbox（红色）和预测框 bbox（绿色）
        if gt_bbox and len(gt_bbox) == 4:
            processed_img = draw_bbox(processed_img, gt_bbox, color="red", width=2) # 红色表示真实框
        if pred_bbox and len(pred_bbox) == 4:
            processed_img = draw_bbox(processed_img, pred_bbox, color="green", width=2) # 绿色表示预测框

        # 保存处理后的图片到 bad_case_img 文件夹，使用唯一的名称
        processed_image_save_path = os.path.join(bad_case_img_dir, unique_file_name)
        try:
            processed_img.save(processed_image_save_path)
            print(f'✅ 处理后的 bad case 图像已保存: {unique_file_name} 到 {bad_case_img_dir}')
            
            # 收集 bad case 的信息
            bad_cases_output_data.append({
                'file_name': file_name, # 原始文件名
                'instruction': instruction,
                'rewritten_query': rewritten_query,
                '处理好的url': os.path.abspath(processed_image_save_path) # 输出绝对路径
            })
        except Exception as e:
            print(f'❌ 无法保存或复制处理后的图像 {unique_file_name}: {e}')
            continue

print(f"\n处理完成。共识别到并处理 {bad_case_count} 个 bad case。")

# 将 bad case 详细信息输出到 CSV 文件
if bad_cases_output_data:
    csv_output_path = './bad_cases.csv'
    with open(csv_output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["file_name", "instruction", "rewritten_query", "处理好的url"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader() # 写入 CSV 表头
        for item_data in bad_cases_output_data:
            writer.writerow(item_data) # 写入每一行数据
    print(f"\nBad case 详细信息已保存到：{csv_output_path}")
else:
    print("\n太棒了！没有找到任何 bad case。")
