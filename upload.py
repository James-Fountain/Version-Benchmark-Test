import requests
from typing import Optional
import os

def upload_file_to_oss(file_path: str) -> Optional[str]:
    """
    上传文件到OSS服务器
    
    Args:
        file_path (str): 要上传的文件的本地路径
        
    Returns:
        Optional[str]: 上传成功返回文件URL，失败返回None
    """
    url = "https://test-front-gw.yingdao.com/gw-api/upload/file"
    
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"错误：文件 {file_path} 不存在")
            return None
            
        # 准备文件数据
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
            
            # 发送POST请求
            response = requests.post(
                url,
                files=files,
                headers={
                    'Accept': 'application/json',
                }
            )
            
            # 检查响应状态（200和201都表示成功）
            if response.status_code in [200, 201]:
                result = response.json()
                if result.get('success') or result.get('code') in [200, 0]:
                    return result.get('data', {}).get('readUrl')
                else:
                    print(f"上传失败：{result.get('message', '未知错误')}")
                    return None
            else:
                print(f"上传失败，状态码：{response.status_code}")
                print(f"错误信息：{response.text}")
                return None
                
    except Exception as e:
        print(f"上传过程中发生错误：{str(e)}")
        return None

# 使用示例
if __name__ == "__main__":
    # 测试上传
    file_path = "test.txt"  # 替换为实际的文件路径
    result = upload_file_to_oss(file_path)
    if result:
        print(f"文件上传成功，URL: {result}")
    else:
        print("文件上传失败")
