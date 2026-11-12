import json
from tools import get_city_lat_lon, get_weather_by_city, get_weather_by_lat_lon

# 工具元数据定义，供LLM识别可用工具
TOOL_LIST = [
    {
        "name": "get_city_lat_lon",
        "description": "输入城市中文名称，查询该城市对应的纬度、经度坐标",
        "parameters": {
            "type": "object",
            "required": ["city"],
            "properties": {
                "city": {"type": "string", "description": "城市名称，例如北京、宁德市"}
            }
        }
    },
    {
        "name": "get_weather_by_city",
        "description": "输入城市名称，直接查询该城市当前天气和未来3天预报",
        "parameters": {
            "type": "object",
            "required": ["city"],
            "properties": {
                "city": {"type": "string", "description": "城市名称，例如上海、广州市"}
            }
        }
    },
    {
        "name": "get_weather_by_lat_lon",
        "description": "输入纬度、经度数值，根据地理坐标查询天气",
        "parameters": {
            "type": "object",
            "required": ["latitude", "longitude"],
            "properties": {
                "latitude": {"type": "number", "description": "纬度浮点数"},
                "longitude": {"type": "number", "description": "经度浮点数"}
            }
        }
    }
]

# 工具名与函数映射
TOOL_FUNC_MAP = {
    "get_city_lat_lon": get_city_lat_lon,
    "get_weather_by_city": get_weather_by_city,
    "get_weather_by_lat_lon": get_weather_by_lat_lon
}

def parse_tool_call(response_text: str):
    """解析模型输出的工具调用JSON"""
    print(f"[ToolParser] 开始解析模型输出，检测工具调用JSON")
    try:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start == -1 or end <= start:
            print(f"[ToolParser] 未检测到工具调用JSON，无需调用工具")
            return None
        json_str = response_text[start:end]
        tool_call = json.loads(json_str)
        print(f"[ToolParser] 解析成功，工具调用结构：{json.dumps(tool_call, ensure_ascii=False)}")
        return tool_call
    except Exception as e:
        print(f"[ToolParser] 解析工具调用失败，异常：{str(e)}")
        return None

def execute_tool(tool_call: dict):
    """执行对应工具函数并返回结果"""
    tool_name = tool_call.get("name")
    params = tool_call.get("parameters", {})
    print(f"[ToolExecutor] 准备执行工具：{tool_name}，入参：{params}")
    func = TOOL_FUNC_MAP.get(tool_name)
    if not func:
        err_msg = f"不存在工具：{tool_name}"
        print(f"[ToolExecutor] {err_msg}")
        return err_msg
    try:
        tool_result = func(**params)
        print(f"[ToolExecutor] 工具执行完成，返回结果长度：{len(tool_result)}")
        return tool_result
    except Exception as e:
        err_msg = f"工具执行异常：{str(e)}"
        print(f"[ToolExecutor] {err_msg}")
        return err_msg