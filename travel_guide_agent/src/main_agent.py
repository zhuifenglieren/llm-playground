"""
主Agent模块 - 负责协调子Agent并统一输出
"""
import asyncio
import json
import re
from typing import Dict, Any, Tuple, Optional
from .sub_agents import WeatherSubAgent, TransportationSubAgent, AttractionsSubAgent


class TravelGuideMainAgent:
    """旅游指南主Agent"""

    def __init__(self):
        self.weather_agent = WeatherSubAgent()
        self.transportation_agent = TransportationSubAgent()
        self.attractions_agent = AttractionsSubAgent()

    def parse_user_input(self, user_input: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析用户输入，提取出发地和目的地
        支持格式：
        - "我想去北京玩，从上海出发，有什么推荐的吗"
        - "从上海去北京玩"
        - "北京旅游推荐"
        """
        origin = None
        destination = None

        # 提取目的地
        dest_patterns = [
            r'去([\u4e00-\u9fa5]{2,10})玩',
            r'去([\u4e00-\u9fa5]{2,10})旅游',
            r'去([\u4e00-\u9fa5]{2,10})',
            r'([\u4e00-\u9fa5]{2,10})旅游推荐',
            r'([\u4e00-\u9fa5]{2,10})旅游攻略'
        ]

        for pattern in dest_patterns:
            match = re.search(pattern, user_input)
            if match:
                destination = match.group(1)
                break

        # 提取出发地
        origin_patterns = [
            r'从([\u4e00-\u9fa5]{2,10})出发',
            r'([\u4e00-\u9fa5]{2,10})出发',
            r'从([\u4e00-\u9fa5]{2,10})去'
        ]

        for pattern in origin_patterns:
            match = re.search(pattern, user_input)
            if match:
                origin = match.group(1)
                break

        # 如果没有明确目的地，尝试提取城市名
        if not destination:
            # 常见城市列表
            cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆",
                      "西安", "南京", "武汉", "长沙", "厦门", "青岛", "大连",
                      "苏州", "天津", "郑州", "昆明", "丽江", "三亚"]

            for city in cities:
                if city in user_input:
                    destination = city
                    break

        # 如果没有出发地，默认使用"当前位置"
        if not origin:
            origin = "当前位置"

        return origin, destination

    async def execute_agents_parallel(self, origin: str, destination: str) -> Dict[str, Any]:
        """
        并行执行三个子Agent
        即使某个Agent失败，其他Agent的结果仍然返回
        """
        # 创建三个子Agent任务
        weather_task = self.weather_agent.execute(destination=destination)
        transport_task = self.transportation_agent.execute(origin=origin, destination=destination)
        attractions_task = self.attractions_agent.execute(destination=destination)

        # 并行执行所有任务
        results = await asyncio.gather(
            weather_task,
            transport_task,
            attractions_task,
            return_exceptions=True
        )

        # 处理结果
        weather_result = results[0] if not isinstance(results[0], Exception) else self._get_error_result("weather",
                                                                                                         destination)
        transport_result = results[1] if not isinstance(results[1], Exception) else self._get_error_result(
            "transportation", destination)
        attractions_result = results[2] if not isinstance(results[2], Exception) else self._get_error_result(
            "attractions", destination)

        return {
            "weather": weather_result,
            "transportation": transport_result,
            "attractions": attractions_result
        }

    def _get_error_result(self, agent_type: str, destination: str) -> Dict[str, Any]:
        """获取错误结果"""
        if agent_type == "weather":
            return {
                "status": "error",
                "source": "none",
                "data": self.weather_agent._get_default_fallback({"destination": destination})
            }
        elif agent_type == "transportation":
            return {
                "status": "error",
                "source": "none",
                "data": self.transportation_agent._get_default_fallback({"destination": destination})
            }
        else:
            return {
                "status": "error",
                "source": "none",
                "data": self.attractions_agent._get_default_fallback({"destination": destination})
            }

    async def process_query(self, user_input: str) -> Dict[str, Any]:
        """
        处理用户查询
        返回统一格式的结果
        """
        # 解析用户输入
        origin, destination = self.parse_user_input(user_input)

        if not destination:
            return {
                "error": "无法识别目的地，请提供更明确的信息",
                "origin": origin,
                "destination": destination
            }

        # 并行执行子Agent
        results = await self.execute_agents_parallel(origin, destination)

        # 统一格式化输出
        return {
            "origin": origin,
            "destination": destination,
            "weather": results["weather"],
            "transportation": results["transportation"],
            "attractions": results["attractions"],
            "timestamp": self._get_timestamp()
        }

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")