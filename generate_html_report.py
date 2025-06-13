import csv
import os

def generate_html_report(csv_file_path, output_html_path):
    """生成一个HTML报告，包含bad case的详细信息和处理后的图片。"""
    html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bad Case 报告</title>
    <style>
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
            vertical-align: top;
        }
        th {
            background-color: #f2f2f2;
        }
        img {
            max-width: 200px;
            height: auto;
            display: block;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <h1>Bad Case 详细报告</h1>
    <table>
        <thead>
            <tr>
                <th>文件名称</th>
                <th>指令</th>
                <th>重写查询</th>
                <th>处理图片</th>
            </tr>
        </thead>
        <tbody>
    """

    try:
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                file_name = row.get('file_name', 'N/A')
                instruction = row.get('instruction', 'N/A')
                rewritten_query = row.get('rewritten_query', 'N/A')
                image_local_path = row.get('处理好的url', '')

                relative_image_path = ""
                if image_local_path:
                    # 尝试从绝对路径中提取相对路径，假设bad_case_img文件夹在生成html的同级目录
                    # 示例: C:\Users\...\bad_case_img\image.png
                    # 目标: bad_case_img/image.png
                    # 在Windows上，split()可能会返回带有反斜杠的路径组件
                    # os.sep 会根据操作系统返回正确的路径分隔符

                    # 1. 尝试找到 'bad_case_img' 所在的索引
                    try:
                        parts = image_local_path.split(os.sep)
                        bad_case_img_index = -1
                        for i, part in enumerate(parts):
                            if part.lower() == 'bad_case_img':
                                bad_case_img_index = i
                                break

                        if bad_case_img_index != -1:
                            # 获取 'bad_case_img' 及其后的所有部分
                            relative_image_path = os.path.join(*parts[bad_case_img_index:])
                            # 统一路径分隔符为 / 适用于HTML
                            relative_image_path = relative_image_path.replace(os.sep, '/')
                        else:
                            # 如果没有找到 'bad_case_img'，则尝试直接使用文件名（作为备用方案）
                            # 或者，如果这个URL可能是完全的外部URL，保持原样
                            if image_local_path.startswith(('http://', 'https://')):
                                relative_image_path = image_local_path
                            else:
                                # 假设是本地路径，但格式不符合预期，直接尝试使用 basename
                                relative_image_path = os.path.join('bad_case_img', os.path.basename(image_local_path)).replace(os.sep, '/')

                    except Exception as path_e:
                        print(f"处理图片路径时发生错误 ({image_local_path}): {path_e}")
                        relative_image_path = ""

                print(f"文件: {file_name}, 处理后的图片路径: {relative_image_path}") # 打印生成的路径

                html_content += f"""
            <tr>
                <td>{file_name}</td>
                <td>{instruction}</td>
                <td>{rewritten_query}</td>
                <td><img src="{relative_image_path}" alt="{file_name}"></td>
            </tr>
                """
    except FileNotFoundError:
        print(f"错误：未找到CSV文件：{csv_file_path}")
        return
    except Exception as e:
        print(f"读取CSV或生成HTML时发生错误：{e}")
        return

    html_content += """
        </tbody>
    </table>
</body>
</html>
    """

    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"HTML报告已生成到：{output_html_path}")

if __name__ == "__main__":
    csv_input_file = './bad_cases.csv'
    output_html_file = './bad_cases_report.html'
    generate_html_report(csv_input_file, output_html_file) 