import json
import os
import shutil
import urllib.request
from PIL import Image, ImageDraw # Required for image manipulation
from datasets import load_dataset # Required to get original images

# --- Helper functions (copied from run_benchmark.py and adapted) ---
def normalize_bbox(bbox_x1y1x2y2, img_width, img_height):
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
    """在图像上绘制边界框"""
    draw = ImageDraw.Draw(image)
    # 确保边界框坐标在图像范围内且顺序正确
    x1, y1, x2, y2 = bbox
    # Convert normalized to pixel coordinates
    img_width, img_height = image.size
    x1 = max(0, x1 * img_width)
    y1 = max(0, y1 * img_height)
    x2 = min(img_width, x2 * img_width)
    y2 = min(img_height, y2 * img_height)
    draw.rectangle([x1, y1, x2, y2], outline=color, width=width)
    return image
# --- End Helper functions ---

# 设置路径
json_path = './results/predictions.json'
visual_dir = './results/visualizations' # Directory for original/downloaded images
bad_case_img_dir = './bad_case_img'    # Directory for processed bad case images

# 确保输出目录存在
os.makedirs(visual_dir, exist_ok=True)
os.makedirs(bad_case_img_dir, exist_ok=True)

print("正在加载 ScreenSpot_v2 测试集以获取原始图片...")
dataset = load_dataset("HongxinLi/ScreenSpot_v2")["test"]
# Create a dictionary to easily access images by file_name
original_image_map = {example["file_name"]: example["image"] for example in dataset}
print("原始图片数据集加载完成。")


# 加载 JSON 文件
if not os.path.exists(json_path):
    print(f"错误：预测文件未找到，路径为 {json_path}")
    exit() # Exit if predictions file not found

try:
    with open(json_path, 'r', encoding='utf-8') as f:
        predictions = json.load(f)
except json.JSONDecodeError:
    print(f"错误：无法解析 JSON 文件 {json_path}，请检查文件格式。")
    exit()

print("开始处理 bad cases...")

bad_case_count = 0

# 处理每一个样本
for item in predictions:
    file_name = item.get('file_name')
    oss_url = item.get('oss_url')
    pred_bbox = item.get('bbox', []) # Predicted bounding box
    gt_bbox = item.get('gt_bbox', []) # Ground truth bounding box

    # 判断是否是 bad case (只要hit_top1, overlap_top1, hit_topk, overlap_topk 中任意一个不为 1，即是 bad case)
    if not (item.get('hit_top1') == 1 and item.get('overlap_top1') == 1 and \
            item.get('hit_topk') == 1 and item.get('overlap_topk') == 1):
        
        bad_case_count += 1
        
        # 获取原始图像
        original_img = original_image_map.get(file_name)
        if not original_img:
            print(f"警告：未找到文件 {file_name} 的原始图像。尝试从OSS下载。")
            local_image_path_in_visuals = os.path.join(visual_dir, file_name)
            if not os.path.exists(local_image_path_in_visuals):
                if oss_url:
                    try:
                        print(f'📥 Downloading image: {file_name} from {oss_url}')
                        urllib.request.urlretrieve(oss_url, local_image_path_in_visuals)
                        original_img = Image.open(local_image_path_in_visuals)
                    except Exception as e:
                        print(f'❌ Failed to download or open {file_name} from {oss_url}: {e}')
                        continue # Skip this bad case if image cannot be obtained
                else:
                    print(f"警告：文件 {file_name} 既没有原始图像映射也没有OSS URL。跳过。")
                    continue
            else:
                original_img = Image.open(local_image_path_in_visuals)

        if not original_img: # Fallback if image still couldn't be loaded
            print(f"错误：无法获取 {file_name} 的图像。跳过该 bad case。")
            continue
        
        # 复制一份图片用于绘制
        processed_img = original_img.copy()

        # 绘制边界框
        # 用户指定：gt_bbox（红色，表示真实框）和bbox（绿色，表示预测框）
        if gt_bbox and len(gt_bbox) == 4:
            processed_img = draw_bbox(processed_img, gt_bbox, color="red", width=2) # 红色表示真实框
        if pred_bbox and len(pred_bbox) == 4:
            processed_img = draw_bbox(processed_img, pred_bbox, color="green", width=2) # 绿色表示预测框

        # 保存处理后的图片到 bad_case_img 文件夹
        processed_image_save_path = os.path.join(bad_case_img_dir, file_name)
        try:
            processed_img.save(processed_image_save_path)
            print(f'✅ Processed bad case image saved: {file_name} to {bad_case_img_dir}')
            
        except Exception as e:
            print(f'❌ Failed to save or copy processed image {file_name}: {e}')
            continue

print(f"\n处理完成。共识别到并处理 {bad_case_count} 个 bad case。Bad case 图片已保存到 {bad_case_img_dir}")

