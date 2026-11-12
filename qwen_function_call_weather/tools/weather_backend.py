import sys
import os
# ========== 路径修复代码，放在最顶部 ==========
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "..")
sys.path.insert(0, os.path.abspath(project_root))

import httpx
import argparse
from config.settings import GEOCODING_URL, WEATHER_URL

# Open-Meteo 天气代码 → 中文描述映射
WEATHER_CODE_MAP = {
    0: "晴天", 1: "大致晴朗", 2: "局部多云", 3: "阴天",
    45: "雾", 48: "冻雾",
    51: "小毛毛雨", 53: "中毛毛雨", 55: "大毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
    95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
}


def get_city_lat_lon(city: str) -> str:
    """
    根据城市名称查询对应经纬度坐标
    Args:
        city: 城市名称，支持中文，例如 "宁德"、"北京"
    Returns:
        城市名称、所属行政区、纬度、经度文本
    """
    print(f"[WeatherTool] 启动城市坐标查询，目标城市：{city}")
    with httpx.Client(timeout=10.0) as client:
        def _geocode(name: str):
            print(f"[WeatherTool] 请求地理编码接口，查询名称：{name}")
            resp = client.get(GEOCODING_URL, params={
                "name": name, "count": 10, "language": "zh", "format": "json",
            })
            resp.raise_for_status()
            return resp.json().get("results") or []

        results = _geocode(city)
        is_low_admin = all(
            str(r.get("feature_code", "")).startswith("PPL")
            and not str(r.get("feature_code", "")).startswith("PPLA")
            for r in results
        ) if results else True
        has_suffix = any(city.endswith(s) for s in ("市", "县", "区", "镇"))
        if is_low_admin and not has_suffix:
            print(f"[WeatherTool] 初次匹配为村镇级地点，自动补充「市」重试查询")
            retry = _geocode(city + "市")
            if retry:
                results = retry

        if not results:
            err_msg = f"未找到城市 '{city}'，请尝试补充市/县后缀重新查询"
            print(f"[WeatherTool] {err_msg}")
            return err_msg

        def _rank(r):
            fc = str(r.get("feature_code", ""))
            admin_priority = 1 if fc.startswith("PPLA") or fc.startswith("ADM") else 0
            pop = r.get("population") or 0
            return (admin_priority, pop)

        loc = max(results, key=_rank)
        lat = loc["latitude"]
        lon = loc["longitude"]
        city_name = loc.get("name", city)
        country = loc.get("country", "")
        admin1 = loc.get("admin1", "")
        print(f"[WeatherTool] 匹配最优地点：{country} {admin1} {city_name}，坐标 lat={lat:.2f}, lon={lon:.2f}")

        return (
            f"城市信息：{country} {admin1} {city_name}\n"
            f"纬度latitude：{lat:.2f}\n"
            f"经度longitude：{lon:.2f}"
        )


def get_weather_by_lat_lon(latitude: float, longitude: float) -> str:
    """
    根据经纬度直接查询当前天气+未来3天预报
    Args:
        latitude: 纬度数值
        longitude: 经度数值
    Returns:
        坐标对应地点完整天气文字报告
    """
    print(f"[WeatherTool] 启动坐标天气查询，纬度：{latitude} 经度：{longitude}")
    # 校验经纬度合法范围
    if not (-90 <= latitude <= 90):
        err_msg = f"纬度 {latitude} 非法，范围必须在 [-90, 90]"
        print(f"[WeatherTool] {err_msg}")
        return err_msg
    if not (-180 <= longitude <= 180):
        err_msg = f"经度 {longitude} 非法，范围必须在 [-180, 180]"
        print(f"[WeatherTool] {err_msg}")
        return err_msg

    with httpx.Client(timeout=10.0) as client:
        try:
            print(f"[WeatherTool] 请求气象预报接口...")
            weather_resp = client.get(WEATHER_URL, params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
                "timezone": "Asia/Shanghai",
                "forecast_days": 3,
            })
            weather_resp.raise_for_status()
        except httpx.RequestError as e:
            err_msg = f"坐标天气数据获取失败：{str(e)}"
            print(f"[WeatherTool] {err_msg}")
            return err_msg

        data = weather_resp.json()
        cur = data["current"]
        daily = data["daily"]
        print(f"[WeatherTool] 气象数据拉取成功，解析当前温度：{cur['temperature_2m']}℃")

        weather_desc = WEATHER_CODE_MAP.get(cur["weather_code"], f"代码{cur['weather_code']}")
        lines = [
            f"【坐标 {latitude:.2f}°N, {longitude:.2f}°E】天气报告",
            "",
            f"当前天气：{weather_desc}",
            f"  温度：{cur['temperature_2m']}°C",
            f"  相对湿度：{cur['relative_humidity_2m']}%",
            f"  风速：{cur['wind_speed_10m']} km/h",
            "",
            "未来3天预报：",
        ]
        for i in range(3):
            day_desc = WEATHER_CODE_MAP.get(daily["weather_code"][i], "")
            lines.append(
                f"  {daily['time'][i]}：{day_desc}，"
                f"{daily['temperature_2m_max'][i]}°C / {daily['temperature_2m_min'][i]}°C，"
                f"降水 {daily['precipitation_sum'][i]} mm"
            )
        report_text = "\n".join(lines)
        print(f"[WeatherTool] 天气报告生成完成")
        return report_text


def get_weather_by_city(city: str) -> str:
    """
    原始函数封装：输入城市名，自动解析坐标并查询天气
    Args:
        city: 城市名称
    Returns:
        城市完整天气报告
    """
    print(f"[WeatherTool] 城市天气一体化查询流程启动，城市：{city}")
    with httpx.Client(timeout=10.0) as client:
        def _geocode(name: str):
            print(f"[WeatherTool] 先解析城市坐标：{name}")
            resp = client.get(GEOCODING_URL, params={
                "name": name, "count": 10, "language": "zh", "format": "json",
            })
            resp.raise_for_status()
            return resp.json().get("results") or []

        results = _geocode(city)
        is_low_admin = all(
            str(r.get("feature_code", "")).startswith("PPL")
            and not str(r.get("feature_code", "")).startswith("PPLA")
            for r in results
        ) if results else True
        has_suffix = any(city.endswith(s) for s in ("市", "县", "区", "镇"))
        if is_low_admin and not has_suffix:
            print(f"[WeatherTool] 补充市后缀重新解析坐标")
            retry = _geocode(city + "市")
            if retry:
                results = retry

        if not results:
            err_msg = f"未找到城市 '{city}'，请尝试其他写法（如补充市字）"
            print(f"[WeatherTool] {err_msg}")
            return err_msg

        def _rank(r):
            fc = str(r.get("feature_code", ""))
            admin_priority = 1 if fc.startswith("PPLA") or fc.startswith("ADM") else 0
            pop = r.get("population") or 0
            return (admin_priority, pop)

        loc = max(results, key=_rank)
        lat = loc["latitude"]
        lon = loc["longitude"]
        city_name = loc.get("name", city)
        country = loc.get("country", "")
        admin1 = loc.get("admin1", "")
        print(f"[WeatherTool] 解析完成坐标 lat={lat:.2f}, lon={lon:.2f}，进入天气查询")

        return get_weather_by_lat_lon(lat, lon)


def loop_interactive():
    """循环交互模式，持续输入城市查询，输入exit退出"""
    print("==================== 循环天气查询工具 ====================")
    print("指令说明：")
    print("1. 直接输入城市名 → 查询该城市天气")
    print("2. loc 城市名 → 查询城市经纬度，例：loc 上海")
    print("3. lat lon → 根据坐标查天气，例：30.52 114.31")
    print("4. exit → 退出循环程序")
    print("=========================================================\n")
    while True:
        user_input = input("请输入查询指令：").strip()
        if not user_input:
            print("输入不能为空，请重新输入\n")
            continue
        if user_input.lower() == "exit":
            print("循环查询程序已退出")
            break
        parts = user_input.split()
        # loc 城市名
        if parts[0] == "loc" and len(parts) >= 2:
            city = "".join(parts[1:])
            res = get_city_lat_lon(city)
            print(f"\n查询结果：\n{res}\n")
        # 两个数字：纬度 经度
        elif len(parts) == 2:
            try:
                lat = float(parts[0])
                lon = float(parts[1])
                res = get_weather_by_lat_lon(lat, lon)
                print(f"\n查询结果：\n{res}\n")
            except ValueError:
                city = user_input
                res = get_weather_by_city(city)
                print(f"\n查询结果：\n{res}\n")
        # 纯城市名称
        else:
            city = user_input
            res = get_weather_by_city(city)
            print(f"\n查询结果：\n{res}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="天气查询工具，支持命令行单次查询或 --loop 循环交互")
    subparsers = parser.add_subparsers(dest="cmd", required=False)

    # 子命令1：城市查天气
    parser_city = subparsers.add_parser("weather-city", help="根据城市查天气")
    parser_city.add_argument("--city", required=True)

    # 子命令2：城市查坐标
    parser_loc = subparsers.add_parser("get-loc", help="根据城市查经纬度")
    parser_loc.add_argument("--city", required=True)

    # 子命令3：坐标查天气
    parser_latlon = subparsers.add_parser("weather-latlon", help="根据经纬度查天气")
    parser_latlon.add_argument("--lat", type=float, required=True)
    parser_latlon.add_argument("--lon", type=float, required=True)

    # 新增循环交互参数
    parser.add_argument("--loop", action="store_true", help="开启持续循环交互模式")
    args = parser.parse_args()

    # 开启循环交互模式
    if args.loop:
        loop_interactive()
    else:
        # 原有单次命令模式
        if not args.cmd:
            print("缺少子命令，可使用 --loop 进入循环交互模式")
            sys.exit(1)
        print(f"[CLI] 命令行工具启动，执行指令：{args.cmd}")
        if args.cmd == "weather-city":
            print(get_weather_by_city(args.city))
        elif args.cmd == "get-loc":
            print(get_city_lat_lon(args.city))
        elif args.cmd == "weather-latlon":
            print(get_weather_by_lat_lon(args.lat, args.lon))