"""
子Agent模块 - 包含天气、交通、景点三个子Agent
"""
import os
import json
from typing import Optional, Dict, Any
from datetime import datetime
import dashscope
from dashscope import Generation
from .api_client import APIClient


class BaseSubAgent:
    """子Agent基类"""

    def __init__(self, name: str):
        self.name = name
        self.api_client = APIClient()
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if self.api_key:
            dashscope.api_key = self.api_key

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行子Agent任务"""
        raise NotImplementedError

    async def _fallback_with_llm(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """使用大模型兜底输出"""
        try:
            if not self.api_key:
                return self._get_default_fallback(context)

            response = Generation.call(
                model="qwen-max",
                messages=[
                    {"role": "system", "content": "你是一个旅游助手，请根据用户需求提供准确的信息。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            if response.status_code == 200:
                result_text = response.output.text
                return self._parse_llm_response(result_text, context)
            else:
                return self._get_default_fallback(context)

        except Exception as e:
            print(f"LLM兜底失败: {e}")
            return self._get_default_fallback(context)

    def _get_default_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """默认兜底数据"""
        raise NotImplementedError

    def _parse_llm_response(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """解析LLM响应"""
        raise NotImplementedError


class WeatherSubAgent(BaseSubAgent):
    """天气查询子Agent"""

    def __init__(self):
        super().__init__("weather_agent")

    async def execute(self, destination: str, **kwargs) -> Dict[str, Any]:
        """执行天气查询"""
        # 优先调用免费API
        weather_data = await self.api_client.get_weather(destination)

        if weather_data and weather_data.get("daily"):
            return {
                "status": "success",
                "source": "api",
                "data": weather_data
            }

        # API失败，使用大模型兜底
        prompt = f"请生成{destination}未来7天的天气预报信息，包括日期、最高温度、最低温度、天气状况和降水概率。请以JSON格式返回。"
        fallback_data = await self._fallback_with_llm(prompt, {"destination": destination})

        return {
            "status": "fallback",
            "source": "llm",
            "data": fallback_data
        }

    def _get_default_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """默认天气数据"""
        destination = context.get("destination", "")
        today = datetime.now()
        daily = []

        for i in range(7):
            date = today.strftime("%Y-%m-%d")
            daily.append({
                "date": date,
                "max_temp": 20 + i,
                "min_temp": 10 + i,
                "weather_desc": "晴朗",
                "weather_code": 0,
                "precipitation_prob": 10
            })

        return {
            "city": destination,
            "country": "",
            "daily": daily
        }

    def _parse_llm_response(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 尝试提取JSON
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                json_str = text[start:end]
                data = json.loads(json_str)
                return data
        except:
            pass

        return self._get_default_fallback(context)


class TransportationSubAgent(BaseSubAgent):
    """交通方式查询子Agent"""

    def __init__(self):
        super().__init__("transportation_agent")

    async def execute(self, origin: str, destination: str, **kwargs) -> Dict[str, Any]:
        """执行交通方式查询"""
        # 优先调用免费API
        transport_data = await self.api_client.get_transportation(origin, destination)

        if transport_data and transport_data.get("options"):
            return {
                "status": "success",
                "source": "api",
                "data": transport_data
            }

        # API失败，使用大模型兜底
        prompt = f"请推荐从{origin}到{destination}的4种交通方式，包括交通类型、预计时间、费用、优势和适合人群。请以JSON格式返回。"
        fallback_data = await self._fallback_with_llm(prompt, {"origin": origin, "destination": destination})

        return {
            "status": "fallback",
            "source": "llm",
            "data": fallback_data
        }

    def _get_default_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """默认交通数据"""
        origin = context.get("origin", "")
        destination = context.get("destination", "")

        return {
            "origin": origin,
            "destination": destination,
            "options": [
                {
                    "type": "高铁/动车",
                    "duration": "约2-6小时",
                    "cost": "200-600元",
                    "advantages": "速度快，舒适度高",
                    "suitable_for": "中长途旅行"
                },
                {
                    "type": "飞机",
                    "duration": "约1-3小时",
                    "cost": "500-1500元",
                    "advantages": "速度最快",
                    "suitable_for": "长途旅行"
                },
                {
                    "type": "自驾",
                    "duration": "灵活安排",
                    "cost": "300-800元",
                    "advantages": "自由度最高",
                    "suitable_for": "家庭出游"
                },
                {
                    "type": "长途大巴",
                    "duration": "约5-10小时",
                    "cost": "100-300元",
                    "advantages": "价格便宜",
                    "suitable_for": "预算有限"
                }
            ]
        }

    def _parse_llm_response(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                json_str = text[start:end]
                data = json.loads(json_str)
                return data
        except:
            pass

        return self._get_default_fallback(context)


class AttractionsSubAgent(BaseSubAgent):
    """旅游景点查询子Agent"""

    def __init__(self):
        super().__init__("attractions_agent")

    async def execute(self, destination: str, **kwargs) -> Dict[str, Any]:
        """执行景点查询"""
        # 优先调用免费API
        attractions_data = await self.api_client.get_attractions(destination)

        if attractions_data and attractions_data.get("attractions"):
            return {
                "status": "success",
                "source": "api",
                "data": attractions_data
            }

        # API失败，使用大模型兜底
        prompt = f"请推荐{destination}的5个知名旅游景点，包括景点名称、评分、类别、简介和门票价格。请以JSON格式返回。"
        fallback_data = await self._fallback_with_llm(prompt, {"destination": destination})

        return {
            "status": "fallback",
            "source": "llm",
            "data": fallback_data
        }

    def _get_default_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """默认景点数据"""
        destination = context.get("destination", "")

        return {
            "city": destination,
            "attractions": [
                {
                    "name": f"{destination}著名景点1",
                    "rating": 4.5,
                    "category": "历史文化",
                    "description": "当地知名景点",
                    "ticket": "详见官网"
                },
                {
                    "name": f"{destination}著名景点2",
                    "rating": 4.4,
                    "category": "自然风光",
                    "description": "风景优美",
                    "ticket": "详见官网"
                },
                {
                    "name": f"{destination}著名景点3",
                    "rating": 4.3,
                    "category": "特色街区",
                    "description": "体验当地文化",
                    "ticket": "免费"
                },
                {
                    "name": f"{destination}著名景点4",
                    "rating": 4.2,
                    "category": "博物馆",
                    "description": "了解当地历史",
                    "ticket": "免费"
                },
                {
                    "name": f"{destination}著名景点5",
                    "rating": 4.1,
                    "category": "城市公园",
                    "description": "休闲放松好去处",
                    "ticket": "免费"
                }
            ]
        }

    def _parse_llm_response(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                json_str = text[start:end]
                data = json.loads(json_str)
                return data
        except:
            pass

        return self._get_default_fallback(context)