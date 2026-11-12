react_financial_agent/
├── README.md                   # 综合项目文档（本文档）
├── index.html                  # Web可视化前端页面
├── vectorstore/                # RAG向量持久化目录
│   ├── faiss_index.bin         # FAISS向量索引
│   └── faiss_meta.json         # 年报元数据（公司/年份/页码/文本）
├── evaluation/                 # 评估输出目录
│   └── compare_result.json     # 双版本Agent量化对比报表
├── src/                        # 全部核心源码
│   ├── memory.py               # 长短记忆管理器（会话隔离、自动摘要、历史召回）
│   ├── agent.py                # CLI统一入口，支持session多轮对话
│   ├── react_manual.py         # 手写正则解析ReAct Agent（DashScope qwen-max）
│   ├── react_function_calling.py # FC原生工具调用Agent（DeepSeek）
│   ├── evaluate.py             # 自动化批量评估脚本
│   ├── serve.py                # FastAPI SSE流式Web服务
│   └── tools.py                # 5大工具实现+Function Calling Schema定义
└── requirements.txt            # 依赖清单

1、环境依赖安装
pip install -r requirements.txt

2、环境变量配置

windows powershell
# DashScope（手写manual版、Embedding向量使用）
$env:DASHSCOPE_API_KEY="sk-xxx"
$env:AGENT_MODEL="qwen-max"
# DeepSeek（FC Function Calling版使用）
$env:DEEPSEEK_API_KEY="sk-xxx"

linux/mac
export DASHSCOPE_API_KEY="sk-xxx"
export AGENT_MODEL="qwen-max"
export DEEPSEEK_API_KEY="sk-xxx"

3、CLI单论对话
cd src
# 手写解析版
python agent.py --mode manual --question "贵州茅台2023毛利率"
# FC原生调用版
python agent.py --mode fc --question "宁德时代2023营收"
# 限制最大推理步数
python agent.py --mode manual --max_steps 8 --question "海康威视年报风险"

4、多轮连续对话
# 第一轮
python agent.py --session chat001 --mode manual --question "茅台2023毛利率"
# 第二轮，复用历史上下文，无需重复查询茅台代码
python agent.py --session chat001 --mode manual --question "那五粮液同期毛利率是多少"

5、自动化批量评估

# 输出对比报表至指定路径
python evaluate.py --output ../evaluation/compare_result.json

6、启动Web流式服务
uvicorn serve:app --host 0.0.0.0 --port 8000