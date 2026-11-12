"""
API客户端模块 - 负责调用免费的外部API
"""
import httpx
from datetime import datetime, timedelta
import asyncio
from typing import Optional, Dict, Any, List


class APIClient:
    """API客户端类，用于调用各种免费API"""

    def __init__(self):
        self.timeout = 10  # 10秒超时

    async def get_weather(self, city: str) -> Optional[Dict[str, Any]]:
        """
        获取天气信息 - 使用Open-Meteo免费API
        返回7天天气预报
        """
        try:
            # 首先获取城市坐标
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                geo_response = await client.get(geo_url, params={
                    "name": city,
                    "count": 1,
                    "language": "zh",
                    "format": "json"
                })

                if geo_response.status_code != 200:
                    return None

                geo_data = geo_response.json()
                if not geo_data.get("results"):
                    return None

                location = geo_data["results"][0]
                lat = location["latitude"]
                lon = location["longitude"]

                # 获取天气数据
                weather_url = "https://api.open-meteo.com/v1/forecast"
                weather_response = await client.get(weather_url, params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": ["temperature_2m_max", "temperature_2m_min",
                              "weathercode", "precipitation_probability_mean"],
                    "timezone": "auto",
                    "forecast_days": 7,
                    "language": "zh"
                })

                if weather_response.status_code != 200:
                    return None

                weather_data = weather_response.json()

                # 转换天气代码为中文描述
                weather_codes = {
                    0: "晴朗", 1: "大部晴朗", 2: "多云", 3: "阴天",
                    45: "有雾", 48: "雾凇", 51: "小毛毛雨", 53: "毛毛雨",
                    55: "大毛毛雨", 61: "小雨", 63: "中雨", 65: "大雨",
                    71: "小雪", 73: "中雪", 75: "大雪", 80: "阵雨",
                    81: "中等阵雨", 82: "大阵雨", 95: "雷暴", 96: "雷暴伴冰雹"
                }

                result = {
                    "city": location.get("name", city),
                    "country": location.get("country", ""),
                    "daily": []
                }

                daily = weather_data.get("daily", {})
                for i in range(7):
                    day_info = {
                        "date": daily.get("time", [])[i],
                        "max_temp": daily.get("temperature_2m_max", [])[i],
                        "min_temp": daily.get("temperature_2m_min", [])[i],
                        "weather_code": daily.get("weathercode", [])[i],
                        "weather_desc": weather_codes.get(daily.get("weathercode", [])[i], "未知"),
                        "precipitation_prob": daily.get("precipitation_probability_mean", [])[i]
                    }
                    result["daily"].append(day_info)

                return result

        except Exception as e:
            print(f"天气API调用失败: {e}")
            return None

    async def get_transportation(self, origin: str, destination: str) -> Optional[Dict[str, Any]]:
        """
        获取交通方式信息 - 模拟或使用免费API
        返回推荐的交通方式
        """
        try:
            # 使用免费的路线API（这里模拟，实际可以集成如高德、百度等免费API）
            # 由于免费交通API限制较多，这里返回基于常识的推荐
            transport_options = [
                {
                    "type": "高铁/动车",
                    "duration": "约2-6小时",
                    "cost": "200-600元",
                    "advantages": "速度快，舒适度高，准点率高",
                    "suitable_for": "中长途旅行，追求效率"
                },
                {
                    "type": "飞机",
                    "duration": "约1-3小时",
                    "cost": "500-1500元",
                    "advantages": "速度最快，适合远距离",
                    "suitable_for": "长途旅行，时间紧迫"
                },
                {
                    "type": "自驾",
                    "duration": "灵活安排",
                    "cost": "油费+过路费约300-800元",
                    "advantages": "自由度最高，可沿途游玩",
                    "suitable_for": "家庭出游，喜欢自由行"
                },
                {
                    "type": "长途大巴",
                    "duration": "约5-10小时",
                    "cost": "100-300元",
                    "advantages": "价格便宜，班次多",
                    "suitable_for": "预算有限，不赶时间"
                }
            ]

            return {
                "origin": origin,
                "destination": destination,
                "options": transport_options
            }

        except Exception as e:
            print(f"交通API调用失败: {e}")
            return None

    async def get_attractions(self, city: str) -> Optional[Dict[str, Any]]:
        """
        获取旅游景点信息 - 使用免费API或返回模拟数据
        """
        try:
            # 尝试使用免费的景点API（这里使用模拟数据，实际可集成）
            # 由于免费景点API质量参差不齐，这里返回基于常识的推荐
            attractions_db = {
                "北京": [
                    {"name": "故宫博物院", "rating": 4.8, "category": "历史文化",
                     "description": "明清两代皇宫，世界最大宫殿建筑群", "ticket": "60元"},
                    {"name": "长城", "rating": 4.7, "category": "历史遗迹",
                     "description": "世界文化遗产，中华民族的象征", "ticket": "40元"},
                    {"name": "颐和园", "rating": 4.6, "category": "皇家园林",
                     "description": "保存最完整的皇家园林", "ticket": "30元"},
                    {"name": "天坛", "rating": 4.5, "category": "历史文化",
                     "description": "明清皇帝祭天场所", "ticket": "15元"},
                    {"name": "798艺术区", "rating": 4.4, "category": "文化艺术",
                     "description": "现代艺术聚集地", "ticket": "免费"}
                ],
                "上海": [
                    {"name": "外滩", "rating": 4.7, "category": "城市景观",
                     "description": "万国建筑博览群", "ticket": "免费"},
                    {"name": "迪士尼乐园", "rating": 4.8, "category": "主题乐园",
                     "description": "中国大陆首家迪士尼乐园", "ticket": "399元起"},
                    {"name": "豫园", "rating": 4.5, "category": "古典园林",
                     "description": "明代私人园林", "ticket": "40元"},
                    {"name": "东方明珠", "rating": 4.4, "category": "地标建筑",
                     "description": "上海标志性建筑", "ticket": "180元"},
                    {"name": "田子坊", "rating": 4.3, "category": "特色街区",
                     "description": "上海弄堂文化代表", "ticket": "免费"}
                ],
                "西安": [
                    {"name": "兵马俑", "rating": 4.9, "category": "历史遗迹",
                     "description": "世界第八大奇迹", "ticket": "120元"},
                    {"name": "大雁塔", "rating": 4.6, "category": "历史建筑",
                     "description": "唐代建筑，佛教圣地", "ticket": "50元"},
                    {"name": "西安城墙", "rating": 4.5, "category": "历史遗迹",
                     "description": "保存最完整的古城墙", "ticket": "54元"},
                    {"name": "回民街", "rating": 4.4, "category": "特色街区",
                     "description": "美食天堂", "ticket": "免费"},
                    {"name": "陕西历史博物馆", "rating": 4.7, "category": "博物馆",
                     "description": "华夏宝库", "ticket": "免费"}
                ],
                "成都": [
                    {"name": "大熊猫繁育研究基地", "rating": 4.8, "category": "自然生态",
                     "description": "近距离观赏国宝大熊猫", "ticket": "55元"},
                    {"name": "宽窄巷子", "rating": 4.5, "category": "特色街区",
                     "description": "成都休闲文化代表", "ticket": "免费"},
                    {"name": "武侯祠", "rating": 4.5, "category": "历史文化",
                     "description": "三国文化圣地", "ticket": "50元"},
                    {"name": "锦里", "rating": 4.4, "category": "特色街区",
                     "description": "西蜀第一街", "ticket": "免费"},
                    {"name": "青城山", "rating": 4.6, "category": "自然风光",
                     "description": "道教名山，幽静天下", "ticket": "90元"}
                ]
            }

            # 尝试匹配城市
            attractions = attractions_db.get(city)

            # 如果没有预设数据，尝试使用免费API或其他方式
            if not attractions:
                # 这里可以集成其他免费景点API
                attractions = [
                    {"name": f"{city}著名景点1", "rating": 4.5, "category": "历史文化",
                     "description": "当地知名景点", "ticket": "详见官网"},
                    {"name": f"{city}著名景点2", "rating": 4.4, "category": "自然风光",
                     "description": "风景优美", "ticket": "详见官网"},
                    {"name": f"{city}著名景点3", "rating": 4.3, "category": "特色街区",
                     "description": "体验当地文化", "ticket": "免费"},
                    {"name": f"{city}著名景点4", "rating": 4.2, "category": "博物馆",
                     "description": "了解当地历史", "ticket": "免费"},
                    {"name": f"{city}著名景点5", "rating": 4.1, "category": "城市公园",
                     "description": "休闲放松好去处", "ticket": "免费"}
                ]

            return {
                "city": city,
                "attractions": attractions[:5]  # 只返回前5个
            }

        except Exception as e:
            print(f"景点API调用失败: {e}")
            return None