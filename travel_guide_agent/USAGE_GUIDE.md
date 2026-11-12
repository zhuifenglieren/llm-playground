# Travel‑Guide‑Agent 使用指南
## 项目简介
旅游指南Agent是一个基于Qwen-max大模型的智能旅游助手系统，能够根据用户的旅游需求，智能推荐目的地的天气、交通方式和旅游景点信息
FastAPI提供后端接口，静态HTML前端，浏览器访问 http://127.0.0.1:8000

## 环境准备
### 1. Python版本
推荐 Python 3.12

### 2. 安装依赖
```bash
pip install -r requirements.txt

travel_guide_agent/
├── main.py                    # FastAPI主程序入口
├── src/                       # 源代码目录
│   ├── __init__.py           # 包初始化文件
│   ├── main_agent.py         # 主Agent（协调子Agent）
│   ├── sub_agents.py         # 三个子Agent定义
│   └── api_client.py         # API客户端（调用免费API）
├── static/                    # 静态文件目录
│   └── index.html            # 前端页面
├── requirements.txt          # Python依赖包列表
├── .env                      # 环境变量配置（需自行创建）
└── USAGE_GUIDE.md           # 使用指南（本文件）

python main.py

