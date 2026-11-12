# Qwen1.5 FunctionCall 天气工具项目使用指南
## 项目概述
基于本地 Qwen1.5-0.5B-Chat 实现 Function Call，内置三合一天气工具：
1. 根据城市名称查询经纬度
2. 根据城市名称直接查询3天天气预报
3. 根据经纬度坐标查询3天天气预报
工具底层基于 open-meteo 免费气象接口，无需密钥。

## 目录结构说明
qwen_function_call_weather/
├── main.py # 程序入口主文件
├── USAGE_GUIDE.md # 项目使用文档
├── requirements.txt # 依赖列表
├── config/
│ └── settings.py # 全局配置（模型路径、系统提示词、接口地址）
├── llm/
│ ├── init.py
│ └── qwen_client.py # 本地 Qwen 模型加载推理封装
├── tools/
│ ├── init.py
│ ├── weather_backend.py # 改造后的天气后端工具
│ └── tool_register.py # 工具定义、调用解析、执行调度


## 环境准备
### 1. 依赖安装
```bash
pip install torch transformers accelerate httpx

2. 本地模型准备
提前下载完整 Qwen1.5-0.5B-Chat 权重文件夹
修改 config/settings.py 中 LOCAL_MODEL_PATH 为你的模型本地绝对 / 相对路径

完整对话
python main.py

循环对话 Function Call 程序
python tools\weather_backend.py --loop

# 城市查天气
python tools\weather_backend.py weather-city --city 北京
# 城市查坐标
python tools\weather_backend.py get-loc --city 上海
# 坐标查天气
python tools\weather_backend.py weather-latlon --lat 30.53 --lon 114.30