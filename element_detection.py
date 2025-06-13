import requests
import base64

class ElementVisionDetector:
    """元素视觉检测服务"""

    def __init__(self, api_url: str = "http://39.101.66.49:8574/vision_detector"):
        self.api_url = api_url

    def _url_to_base64(self, image_url):
        response = requests.get(image_url)
        img_data = response.content
        base64_str = base64.b64encode(img_data).decode('utf-8')
        return base64_str

    def detect_element(self, screenshot: str, description: str) :
        """检测元素位置"""
        try:
            # 准备请求数据
            headers = {
                "Content-Type": "application/json"
            }

            data = {
                "query": f"{description}",
                "imgBase64": self._url_to_base64(screenshot)
            }

            # 发送请求
            response = requests.post(
                url=self.api_url,
                json=data,
                headers=headers
            )

            # 检查响应状态
            response.raise_for_status()

            # 解析响应
            result = response.json()
            print(result)
            return {
                "success": True,
                "bbox": result.get("data", {}).get("bbox", [])
            }

        except Exception as e:
            print(f"元素检测失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
if __name__ == "__main__":
    detector = ElementVisionDetector()
    detector.detect_element("", "搜索框")