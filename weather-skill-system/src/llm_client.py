"""
Qwen-max 大模型远程调用客户端
通过 DashScope API 调用通义千问大模型
"""
import json
import requests
from typing import Dict, List, Optional


class LLMClient:
    """大模型调用客户端，封装 DashScope API"""

    def __init__(self, api_key: str, model: str = "qwen-max"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def chat(self, messages: List[Dict], temperature: float = 0.7) -> str:
        """
        对话式调用大模型
        :param messages: 消息列表，格式 [{"role": "user", "content": "..."}]
        :param temperature: 采样温度
        :return: 模型回复内容
        """
        payload = {
            "model": self.model,
            "input": {"messages": messages},
            "parameters": {
                "temperature": temperature,
                "result_format": "message"
            }
        }

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        data = response.json()

        if "output" in data and "choices" in data["output"]:
            return data["output"]["choices"][0]["message"]["content"]
        raise ValueError(f"API 返回格式异常: {data}")

    def structured_output(self, prompt: str, schema: Dict) -> Dict:
        """
        获取结构化 JSON 输出
        :param prompt: 用户提示词
        :param schema: 期望的 JSON Schema
        :return: 解析后的字典
        """
        system_prompt = (
            "你是一个专业的信息提取助手，请严格按照用户提供的 JSON 格式输出结果，"
            "不要添加任何额外解释、markdown 标记或说明文字，只输出纯 JSON。"
            f"\nJSON Schema: {json.dumps(schema, ensure_ascii=False)}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        result = self.chat(messages, temperature=0.1)
        # 清理可能的 markdown 代码块标记
        result = result.strip().strip("```json").strip("```").strip()
        return json.loads(result)