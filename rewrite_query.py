import requests
import json
import time

system_prompt = """
## task description
根据用户提供的图片，其中用红框框出了需要关注的元素，记为关注元素。你需要分析完整网页，对关注元素进行描述。
关注元素的描述用中文输出。

## Element description
- First sentence: briefly and clearly explain what the focus element is. For simple elements, only the first sentence is required.
- Subsequent sentences (if necessary): explain its function, or the logical relationship with other elements in the page, in order to accurately locate the focus element.
- The description must be unique, and it should be able to uniquely point to the target element even if there are multiple similar elements on the page. If the element has multiple identical or similar contents in screenshot, it is necessary to combine other known elements at its level for auxiliary positioning.
- Element descriptions must be precise and actionable, and in Chinese.
- The description should be concise and clear, and should not exceed 100 words.
return 
```json
{
    "element_description": "..."
}
```


"""


def send_gemini25_pro_request(image_url: str, instruction: str):
    url = "http://xybot-appreciation:8080/api/appreciation/v1/inner/completions/vision"

    headers = {
        "xybot-user": json.dumps({
            "tenantUuid": "bad23bd0-b0a3-4e64-a32b-e82661ec2214",
            "organizationUuid": "bb86844a-1e14-4baf-87ed-7c6619c9c383",
            "uuid": "575875007621890048"
        }),
        "Content-Type": "application/json"
    }
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
       {            "role": "user",            "content": [                {                    "type": "text",                    "text": f"红框元素的描述: {instruction}"                },                {                    "type": "image_url",                    "image_url": {                        "url": image_url                    }                }            ]        }
    ]

    data = {
        "aiID": "completion",
        "rule": "langchain",
        "bizId": "221212709355520",
        "bizCode": "ai-power",
        "bizType": "run_flow",
        "extraJson": "额外字段",
        "bizExtra": "业务方额外字段",
        "channel": "gemini",
        "model": "gemini-2.5-flash",
        "messages": messages,
        "temperature": 0,
        "llmKeyJson": "", # 非必填，用户llm_key。 需要与channel对应
        "timeout": 86400,
        "maxTokens": 30000,
         "budgetTokens": 0
    }
    t1 = time.time()
    response = requests.post(url, headers=headers, json=data)
    t2 = time.time()
    time_spand = t2-t1
    try:
        response_json = json.loads(response.text)
        content = response_json["data"]["choices"][0]["message"]["content"]
        # 移除可能的 markdown 格式
        content = content.replace('```json', '').replace('```', '').strip()
        print(f"API返回内容：{content}")
        
        try:
            content_json = json.loads(content)
            return content_json["element_description"], time_spand
        except json.JSONDecodeError as e:
            print(f"JSON解析错误：{e}\n原始内容：{content}")
            return content, time_spand
    except Exception as e:
        print(f"处理响应时出错：{e}")
        return str(e), time_spand
