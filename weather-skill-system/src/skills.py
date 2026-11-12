"""
Skill 定义与注册中心
所有可执行的 skill 在此处定义并注册
"""
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from .llm_client import LLMClient
from .utils import OpenMeteoClient


class BaseSkill(ABC):
    """Skill 基类，所有 skill 必须继承此类"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.name = self.__class__.__name__

    @abstractmethod
    def get_steps(self) -> List[str]:
        """返回该 skill 的执行步骤列表"""
        pass

    @abstractmethod
    def execute_step(self, step_index: int, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行指定步骤，返回更新后的上下文"""
        pass

    def run_full(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """完整执行所有步骤"""
        ctx = context.copy()
        for i in range(len(self.get_steps())):
            ctx = self.execute_step(i, ctx)
        return ctx


class WeatherCardSkill(BaseSkill):
    """
    天气预报卡片生成 Skill（Open-Meteo 真实数据版，无需密钥）
    渐进式执行步骤：
    1. 解析用户输入，提取城市、预报天数
    2. 调用 Open-Meteo 免费API获取真实预报数据
    3. 大模型生成卡片文案与生活建议
    4. 渲染天蓝色主题HTML卡片（支持多日展示）
    """

    def __init__(self, llm_client: LLMClient):
        super().__init__(llm_client)
        self.weather_client = OpenMeteoClient()

    def get_steps(self) -> List[str]:
        return [
            "step1_parse_location",
            "step2_fetch_real_weather",
            "step3_generate_card_content",
            "step4_render_html_card"
        ]

    def execute_step(self, step_index: int, context: Dict[str, Any]) -> Dict[str, Any]:
        steps = self.get_steps()
        method = getattr(self, steps[step_index])
        return method(context)

    def step1_parse_location(self, context: Dict) -> Dict:
        """步骤1：解析城市与预报天数"""
        user_input = context.get("user_input", "北京今天天气")

        schema = {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "具体城市名称，不可为空"},
                "date_desc": {"type": "string", "description": "自然语言日期描述，如今天、明天、未来3天"},
                "forecast_days": {"type": "integer", "description": "预报天数，1-7之间的整数"}
            },
            "required": ["city", "date_desc", "forecast_days"]
        }

        prompt = f"""
        从用户输入中提取天气查询信息：{user_input}
        规则：
        1. city必须是真实存在的城市名，无法识别则留空
        2. forecast_days为预报天数，今天/明天=1，未来N天=N，最多7天
        3. date_desc为自然语言描述，原样提取
        """
        result = self.llm.structured_output(prompt.strip(), schema)
        result["forecast_days"] = min(max(result.get("forecast_days", 1), 1), 7)

        context["location"] = result
        context["current_step"] = "step1_parse_location"
        return context

    def step2_fetch_real_weather(self, context: Dict) -> Dict:
        """步骤2：调用免费API获取真实天气数据"""
        city_name = context["location"]["city"]
        days = context["location"]["forecast_days"]

        # 城市地理编码（转经纬度）
        city_info = self.weather_client.get_city_info(city_name)
        if not city_info:
            raise ValueError(f"无法查询到城市「{city_name}」，请确认城市名称正确")

        # 获取多日预报
        daily_list = self.weather_client.get_daily_forecast(
            lat=city_info["lat"],
            lon=city_info["lon"],
            days=days
        )
        if not daily_list:
            raise RuntimeError("天气数据获取失败，请检查网络连接")

        context["weather_data"] = {
            "city": city_info["name"],
            "daily": daily_list
        }
        context["current_step"] = "step2_fetch_real_weather"
        return context

    def step3_generate_card_content(self, context: Dict) -> Dict:
        """步骤3：生成卡片文案与建议"""
        weather = context["weather_data"]
        first_day = weather["daily"][0]
        date_desc = context["location"]["date_desc"]

        schema = {
            "type": "object",
            "properties": {
                "card_title": {"type": "string", "description": "卡片主标题"},
                "dressing_advice": {"type": "string", "description": "穿搭建议，25字以内"},
                "travel_tip": {"type": "string", "description": "出行提示，25字以内"},
                "comfort_desc": {"type": "string", "description": "整体舒适度评价"}
            },
            "required": ["card_title", "dressing_advice", "travel_tip"]
        }

        prompt = f"""
        基于天气生成卡片文案：
        城市：{weather['city']}
        时段：{date_desc}
        首日天气：{first_day['weather_day']}
        气温：{first_day['temp_min']}°C ~ {first_day['temp_max']}°C
        风力：{first_day['wind_dir']} {first_day['wind_scale']}级
        湿度：{first_day['humidity']}%
        """
        card_content = self.llm.structured_output(prompt.strip(), schema)

        context["card_content"] = card_content
        context["current_step"] = "step3_generate_card_content"
        return context

    def step4_render_html_card(self, context: Dict) -> Dict:
        """步骤4：渲染天蓝色主题多日预报卡片"""
        weather = context["weather_data"]
        content = context["card_content"]
        location = context["location"]
        daily = weather["daily"]

        # 生成每日天气HTML片段
        daily_html = ""
        for day in daily:
            date_short = day["date"][5:]  # 只保留月-日
            daily_html += f"""
            <div class="day-item">
                <div class="day-date">{date_short}</div>
                <div class="day-icon">{day['weather_icon']}</div>
                <div class="day-weather">{day['weather_day']}</div>
                <div class="day-temp">{day['temp_min']}°~{day['temp_max']}°</div>
            </div>
            """

        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{weather['city']}天气预报</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ padding: 20px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
        .weather-card {{
            width: 100%;
            max-width: 500px;
            border-radius: 20px;
            padding: 28px;
            background: linear-gradient(180deg, #B0E0E6 0%, #4A90E2 45%, #2E6FBF 100%);
            color: white;
            box-shadow: 0 15px 50px rgba(74, 144, 226, 0.35);
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 20px;
        }}
        .city-name {{ font-size: 26px; font-weight: 700; }}
        .date-text {{ font-size: 14px; opacity: 0.9; margin-top: 4px; }}
        .card-title {{
            font-size: 18px;
            font-weight: 500;
            text-align: center;
            margin-bottom: 20px;
            opacity: 0.95;
        }}
        .today-overview {{
            display: flex;
            align-items: center;
            justify-content: space-around;
            padding: 18px 0;
            border-bottom: 1px solid rgba(255,255,255,0.2);
            margin-bottom: 18px;
        }}
        .today-icon {{ font-size: 70px; }}
        .today-temp {{ font-size: 46px; font-weight: 700; }}
        .today-desc {{ font-size: 15px; opacity: 0.9; }}
        .daily-forecast {{
            display: flex;
            justify-content: space-between;
            gap: 6px;
            margin-bottom: 18px;
        }}
        .day-item {{
            flex: 1;
            text-align: center;
            padding: 10px 4px;
            background: rgba(255,255,255,0.15);
            border-radius: 10px;
        }}
        .day-date {{ font-size: 12px; opacity: 0.85; margin-bottom: 5px; }}
        .day-icon {{ font-size: 26px; margin-bottom: 3px; }}
        .day-weather {{ font-size: 12px; margin-bottom: 3px; }}
        .day-temp {{ font-size: 13px; font-weight: 600; }}
        .detail-row {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 10px;
            margin-bottom: 16px;
        }}
        .detail-item {{
            background: rgba(255,255,255,0.12);
            padding: 10px;
            border-radius: 10px;
            text-align: center;
            font-size: 13px;
        }}
        .tips-section {{
            background: rgba(255,255,255,0.15);
            border-radius: 12px;
            padding: 14px 16px;
            font-size: 14px;
            line-height: 1.6;
        }}
        .tip-item {{ display: flex; align-items: center; gap: 8px; margin: 3px 0; }}
    </style>
</head>
<body>
    <div class="weather-card">
        <div class="card-header">
            <div>
                <div class="city-name">{weather['city']}</div>
                <div class="date-text">{location['date_desc']} · 实时气象数据</div>
            </div>
        </div>

        <div class="card-title">{content['card_title']}</div>

        <div class="today-overview">
            <div class="today-icon">{daily[0]['weather_icon']}</div>
            <div>
                <div class="today-temp">{daily[0]['temp_min']}°~{daily[0]['temp_max']}°</div>
                <div class="today-desc">{daily[0]['weather_day']} · {daily[0]['wind_dir']} {daily[0]['wind_scale']}级</div>
            </div>
        </div>

        <div class="daily-forecast">
            {daily_html.strip()}
        </div>

        <div class="detail-row">
            <div class="detail-item">💧 湿度 {daily[0]['humidity']}%</div>
            <div class="detail-item">☀️ 紫外线 {daily[0]['uv_index']}级</div>
            <div class="detail-item">🌬️ {daily[0]['wind_scale']}级风</div>
        </div>

        <div class="tips-section">
            <div class="tip-item">👕 {content['dressing_advice']}</div>
            <div class="tip-item">🚶 {content['travel_tip']}</div>
            <div class="tip-item">✨ {content['comfort_desc']}</div>
        </div>
    </div>
</body>
</html>
        """

        context["html_output"] = html_template.strip()
        context["current_step"] = "step4_render_html_card"
        context["status"] = "completed"
        return context


# Skill 注册中心
SKILL_REGISTRY = {
    "weather_card": WeatherCardSkill
}


def get_skill(skill_name: str, llm_client: LLMClient) -> BaseSkill:
    """获取skill实例"""
    if skill_name not in SKILL_REGISTRY:
        raise ValueError(f"未注册的 skill: {skill_name}")
    return SKILL_REGISTRY[skill_name](llm_client)