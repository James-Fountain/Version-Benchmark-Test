import os
import json
import argparse
from datasets import load_dataset
from rewrite_query import send_gemini25_pro_request
from element_detection import ElementVisionDetector
from upload import upload_file_to_oss
from PIL import Image, ImageDraw
import tempfile

def normalize_bbox(bbox_x1y1x2y2, img_width, img_height):
    # if bbox_x1y1x2y2 is not normalized to [0, 1], normalize it
    x1, y1, x2, y2 = bbox_x1y1x2y2
    if (0 <= x1 <= 1) and (0 <= y1 <= 1) and (0 <= x2 <= 1) and (0 <= y2 <= 1):
        return bbox_x1y1x2y2
    else:
        x1 = x1 / img_width
        y1 = y1 / img_height
        x2 = x2 / img_width
        y2 = y2 / img_height
        return x1, y1, x2, y2

def do_boxes_overlap(box1, box2):
    """
    Check if two boxes overlap.
    
    Each box is represented as a tuple: (x1, y1, x2, y2)
    Where (x1, y1) is the top-left and (x2, y2) is the bottom-right corner.
    """
    # 解包两个边界框的坐标，box1 为 (x1_min, y1_min, x1_max, y1_max)，box2 为 (x2_min, y2_min, x2_max, y2_max)。
    x1_min, y1_min, x1_max, y1_max = box1 
    x2_min, y2_min, x2_max, y2_max = box2 

    # 检查不重叠的条件
    if x1_max < x2_min or x2_max < x1_min: 
    # 如果 box1 的右边界 (x1_max) 在 box2 的左边界 (x2_min) 的左边，
    # 或者 box2 的右边界 (x2_max) 在 box1 的左边界 (x1_min) 的左边，
    # 这意味着两个框在水平方向上没有重叠。满足其中一个条件，则它们不重叠。
        return False 
    if y1_max < y2_min or y2_max < y1_min: 
    # 如果 box1 的下边界 (y1_max) 在 box2 的上边界 (y2_min) 的上面，
    # 或者 box2 的下边界 (y2_max) 在 box1 的上边界 (y1_min) 的上面，
    # 这意味着两个框在垂直方向上没有重叠。满足其中一个条件，则它们不重叠。
        return False 

    return True
    # 如果以上任何“不重叠”的条件都不满足，那么就意味着两个边界框在水平和垂直方向上都有重叠，因此它们是重叠的，返回 True。

# 定义域名字典
domain_dict = {
    "windows": "desktop",
    "macos": "desktop",
    "ios": "mobile",
    "android": "mobile",
    "tool": "web",
    "shop": "web",
    "gitlab": "web",
    "forum": "web"
}

def draw_bbox(image, bbox, color="red", width=2):
    """在图像上绘制边界框"""
    draw = ImageDraw.Draw(image)
    # 确保边界框坐标在图像范围内且顺序正确
    x1, y1, x2, y2 = bbox
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)

    x1 = max(0, x1 * image.width)
    y1 = max(0, y1 * image.height)
    x2 = min(image.width, x2 * image.width)
    y2 = min(image.height, y2 * image.height)
    draw.rectangle([x1, y1, x2, y2], outline=color, width=width)
    return image

def process_single_image(image, gt_bbox, instruction):
    """处理单张图片，返回预测结果"""
    try:
        # 1. 在图像中标记红色矩形框
        marked_image = image.copy()
        if gt_bbox:
            marked_image = draw_bbox(marked_image, gt_bbox, color="red", width=2) # 使用红色标记ground truth

        # 2. 将标记后的图片上传到OSS
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            marked_image.save(temp_file.name)
            image_url = upload_file_to_oss(temp_file.name)
            os.unlink(temp_file.name)  # 删除临时文件

        if not image_url:
            print(f"警告：图片上传失败，跳过该样本")
            return [], "", "" # 返回空列表，空字符串，空字符串

        # 3. 调用rewrite_query进行查询改写
        rewritten_query, time_cost = send_gemini25_pro_request(image_url, instruction)
        print(f"Query改写耗时：{time_cost}秒")
        print(f"改写后的查询：{rewritten_query}")
    
        # 4. 调用element_detection进行坐标预测
        detector = ElementVisionDetector()
        result = detector.detect_element(image_url, rewritten_query)
        
        # 将像素坐标转换为归一化坐标
        bbox_pixels = result.get("bbox", [])
        if bbox_pixels and len(bbox_pixels) == 4:
            # 获取原始图像尺寸，这里直接使用传入的image对象获取尺寸
            img_width, img_height = image.size
                
            x1, y1, x2, y2 = bbox_pixels
            normalized_bbox = [
                x1 / img_width,
                y1 / img_height,
                x2 / img_width,
                y2 / img_height
            ]
            return normalized_bbox, image_url, rewritten_query
        return [], image_url, rewritten_query
    except Exception as e:
        print(f"处理图片时发生错误：{e}，跳过该样本")
        return [], "", ""

def main():
    parser = argparse.ArgumentParser(description="运行基准测试评估脚本")
    parser.add_argument("--save_path", type=str, default="./results", help="结果保存目录路径")
    args = parser.parse_args()

    # 确保保存路径和可视化目录存在
    os.makedirs(args.save_path, exist_ok=True)
    vis_dir = os.path.join(args.save_path, "visualizations")
    os.makedirs(vis_dir, exist_ok=True)
    
    # 加载测试数据集
    print("正在加载 ScreenSpot_v2 测试集...")
    dataset = load_dataset("HongxinLi/ScreenSpot_v2")["test"]
    print("ScreenSpot_v2 测试集加载完成。")
    print(dataset[:2])
    print(len(dataset))
    # 需要读取 图片 和 ground truth 把 图像 中的 box 用红框标记一下 。然后调用 rewrite_query 进行查询改写，然后使用改写后的 结果调用 element_detection 进行坐标预测，最后计算评估指标。
    
    pred_path = os.path.join(args.save_path, "predictions.json")
    metric_path = os.path.join(args.save_path, "metrics.txt")

    # 初始化 predictions.json 文件为 JSON 数组的开始
    with open(pred_path, "w", encoding="utf-8") as f:
        f.write("[")

    first_entry = True
    for example_idx, example in enumerate(dataset):
        
        try:
            data_source = example["data_source"]
            # 筛选只包含 "web" 场景的域
            if data_source not in ["tool", "shop", "gitlab", "forum"]:
                print(f"跳过非web场景样本：{example['file_name']} (data_source: {data_source})")
                continue

            image = example["image"]
            instruction = example["instruction"]
            gt_bbox = normalize_bbox(example["bbox"], image.width, image.height)
            
            # 保存原始图像的副本用于可视化
            vis_image = image.copy()
                
            print(f"正在处理图片：{instruction}")
            pred_bbox, oss_url, rewritten_query_content = process_single_image(image, gt_bbox, instruction)
            
            # 初始化评估指标
            hit_top1 = 0
            overlap_top1 = 0
            hit_topk = 0
            overlap_topk = 0

            # 只有当 pred_bbox 和 gt_bbox 都存在时才计算评估指标
            if pred_bbox and gt_bbox:
                # 在可视化图像上绘制边界框
                vis_image = draw_bbox(vis_image, gt_bbox, color="green", width=2)  # 绿色表示真实框
                vis_image = draw_bbox(vis_image, pred_bbox, color="red", width=2)  # 红色表示预测框

                # hit_top1 和 hit_topk 的计算
                # 检查预测框的中心点是否在真实框内
                px = (pred_bbox[0] + pred_bbox[2]) / 2
                py = (pred_bbox[1] + pred_bbox[3]) / 2
                x1, y1, x2, y2 = gt_bbox

                if (x1 <= px <= x2) and (y1 <= py <= y2):
                    hit_top1 = 1
                    hit_topk = 1  # 如果top1命中，topk也命中

                # overlap_top1 和 overlap_topk 的计算
                if do_boxes_overlap(pred_bbox, gt_bbox):
                    overlap_top1 = 1
                    overlap_topk = 1  # 如果top1重叠，topk也重叠
            else:
                # 如果 pred_bbox 或 gt_bbox 不存在，则不绘制预测框，只绘制真实框（如果存在）
                if gt_bbox:
                    vis_image = draw_bbox(vis_image, gt_bbox, color="green", width=2)  # 绿色表示真实框

            # 保存可视化结果
            vis_path = os.path.join(vis_dir, f"{example['file_name']}")
            vis_image.save(vis_path)
            print(f"可视化结果已保存至：{vis_path}")

            current_result = {
                "file_name": example["file_name"],
                "data_type": example["data_type"],
                "domain": domain_dict[data_source],
                "instruction": instruction,
                "img_size": image.size,
                "bbox": pred_bbox,
                "oss_url": oss_url,
                "rewritten_query": rewritten_query_content,
                "gt_bbox": gt_bbox,
                "hit_top1": hit_top1,
                "overlap_top1": overlap_top1,
                "hit_topk": hit_topk,
                "overlap_topk": overlap_topk
            }
        except Exception as e:
            print(f"处理样本 {example.get('file_name', '未知文件')} 时发生错误：{e}，跳过该样本")
            # 即使发生错误，也添加一个记录，确保 predictions.json 文件的完整性
            current_result = {
                "file_name": example.get("file_name", "未知文件"),
                "data_type": example.get("data_type", "N/A"),
                "domain": domain_dict.get(data_source, "N/A"),
                "instruction": instruction,
                "img_size": image.size if 'image' in locals() else "N/A",
                "bbox": [],
                "oss_url": "",
                "rewritten_query": "",
                "gt_bbox": gt_bbox if 'gt_bbox' in locals() else "N/A",
                "hit_top1": 0,
                "overlap_top1": 0,
                "hit_topk": 0,
                "overlap_topk": 0,
                "error": str(e)
            }
        
        # 将当前结果写入 predictions.json 文件
        with open(pred_path, "a", encoding="utf-8") as f:
            if not first_entry:
                f.write(",\n")
            json.dump(current_result, f, ensure_ascii=False, indent=2)
            first_entry = False

    # 结束 predictions.json 文件为 JSON 数组的结尾
    with open(pred_path, "a", encoding="utf-8") as f:
        f.write("]")
    print(f"预测结果已保存至：{pred_path}")
    


if __name__ == "__main__":
    main()