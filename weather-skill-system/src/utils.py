"""
通用工具函数集合
"""
import os
import re
import yaml
import datetime
import requests
from typing import Dict, List, Optional


def load_config(config_path: str = "config/config.yaml") -> Dict:
    """加载 YAML 配置文件"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_api_key(config: Dict, key_name: str = "dashscope_api_key") -> str:
    """获取 API Key，优先读取环境变量"""
    env_key = os.environ.get(key_name.upper())
    if env_key:
        return env_key
    return config.get("api", {}).get(key_name, "")


def validate_config(config: Dict) -> bool:
    """校验配置完整性"""
    required = ["api"]
    for key in required:
        if key not in config:
            return False
    return True


def generate_filename(prefix: str, suffix: str, context: Dict = None, mode: str = "content") -> str:
    """
    生成安全的输出文件名，支持两种命名模式
    :param prefix: 文件名前缀
    :param suffix: 文件后缀
    :param context: 上下文数据，内容模式提取城市与时段
    :param mode: 命名模式：content / timestamp
    """
    def clean_filename(text: str) -> str:
        """移除文件名非法字符，兼容全平台"""
        return re.sub(r'[\\/:*?"<>|\s]', '', text)

    if mode == "content" and context and "location" in context:
        loc = context["location"]
        city = clean_filename(loc.get("city", "unknown"))
        date_desc = clean_filename(loc.get("date_desc", "unknown"))
        name_part = f"{city}_{date_desc}"
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name_part = timestamp

    return f"{prefix}_{name_part}{suffix}"


# ========== Open-Meteo 免费气象API客户端（无需密钥）==========
class OpenMeteoClient:
    """
    Open-Meteo 开源气象API封装，无需注册、无需密钥
    支持城市地理编码、多日预报、天气代码转中文
    """
    GEO_API = "https://geocoding-api.open-meteo.com/v1/search"
    WEATHER_API = "https://api.open-meteo.com/v1/forecast"

    # WMO 国际天气代码 → (中文描述, Emoji图标)
    WEATHER_CODE_MAP = {
        0: ("晴", "☀️"),
        1: ("大部晴朗", "🌤️"),
        2: ("局部多云", "⛅"),
        3: ("阴天", "☁️"),
        45: ("雾", "🌫️"),
        48: ("雾凇", "🌫️"),
        51: ("小毛毛雨", "🌧️"),
        53: ("毛毛雨", "🌧️"),
        55: ("大毛毛雨", "🌧️"),
        56: ("冻毛毛雨", "🌧️"),
        57: ("强冻毛毛雨", "🌧️"),
        61: ("小雨", "🌧️"),
        63: ("中雨", "🌧️"),
        65: ("大雨", "🌧️"),
        66: ("冻雨", "🌧️"),
        67: ("强冻雨", "🌧️"),
        71: ("小雪", "❄️"),
        73: ("中雪", "❄️"),
        75: ("大雪", "❄️"),
        77: ("雪粒", "❄️"),
        80: ("阵雨", "🌦️"),
        81: ("强阵雨", "🌧️"),
        82: ("暴雨", "⛈️"),
        85: ("阵雪", "🌨️"),
        86: ("强阵雪", "❄️"),
        95: ("雷阵雨", "⛈️"),
        96: ("雷阵雨伴冰雹", "⛈️"),
        99: ("强雷暴伴冰雹", "⛈️"),
    }

    @classmethod
    def get_weather_info(cls, code: int) -> tuple[str, str]:
        """天气代码转中文描述+图标"""
        return cls.WEATHER_CODE_MAP.get(code, ("未知", "🌡️"))

    @staticmethod
    def wind_degree_to_dir(degree: float) -> str:
        """风向角度（0-360°）转中文风向"""
        dirs = ["北风", "东北风", "东风", "东南风", "南风", "西南风", "西风", "西北风"]
        idx = round(degree / 45) % 8
        return dirs[idx]

    @staticmethod
    def wind_speed_to_scale(speed_kmh: float) -> int:
        """风速（km/h）转蒲福风力等级（0-12级）"""
        thresholds = [1, 5, 11, 19, 28, 38, 49, 61, 74, 88, 102, 117, 134]
        for level, threshold in enumerate(thresholds):
            if speed_kmh < threshold:
                return level
        return 12

    def get_city_info(self, city_name: str) -> Optional[Dict]:
        """
        城市名查询地理信息
        返回 {"name": 城市名, "lat": 纬度, "lon": 经度}
        查询失败返回 None
        """
        params = {
            "name": city_name,
            "count": 1,
            "language": "zh",
            "format": "json"
        }
        try:
            resp = requests.get(self.GEO_API, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if "results" in data and len(data["results"]) > 0:
                res = data["results"][0]
                return {
                    "name": res.get("name", city_name),
                    "lat": res["latitude"],
                    "lon": res["longitude"]
                }
            return None
        except Exception:
            return None

    def get_daily_forecast(self, lat: float, lon: float, days: int = 3) -> List[Dict]:
        """
        获取多日天气预报
        :param lat: 纬度
        :param lon: 经度
        :param days: 预报天数，最大7天
        :return: 每日天气列表
        """
        days = min(max(days, 1), 7)
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "weather_code",
                "relative_humidity_2m_max",
                "wind_speed_10m_max",
                "wind_direction_10m_dominant",
                "uv_index_max",
                "precipitation_sum"
            ],
            "timezone": "auto",
            "forecast_days": days
        }
        try:
            resp = requests.get(self.WEATHER_API, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            if not dates:
                return []

            result = []
            for i in range(len(dates)):
                code = daily["weather_code"][i]
                weather_desc, weather_icon = self.get_weather_info(code)
                wind_speed = daily["wind_speed_10m_max"][i]
                wind_degree = daily["wind_direction_10m_dominant"][i]

                result.append({
                    "date": dates[i],
                    "temp_max": round(daily["temperature_2m_max"][i]),
                    "temp_min": round(daily["temperature_2m_min"][i]),
                    "weather_day": weather_desc,
                    "weather_icon": weather_icon,
                    "wind_dir": self.wind_degree_to_dir(wind_degree),
                    "wind_scale": self.wind_speed_to_scale(wind_speed),
                    "humidity": round(daily["relative_humidity_2m_max"][i]),
                    "uv_index": round(daily["uv_index_max"][i]),
                    "precip": round(daily["precipitation_sum"][i], 1)
                })
            return result
        except Exception:
            return []