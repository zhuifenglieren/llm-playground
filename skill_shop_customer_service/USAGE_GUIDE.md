# skill_shop_customer_service 使用指南
## 1.项目概述
本电商客服 Skill 工程特性：
1. **全部配置文件采用 Markdown 文件管理**，配置存储于 ```json 代码块，支持头部注释、版本备注、修改记录；
2. 组件懒加载机制，超时之后自动卸载模块，压低常驻内存占用；
3. 内置自进化框架，收集对话指标，调用 Qwen‑max 大模型自动优化全部 md 格式配置；
4. 配置自动备份、优化前后指标对比、可视化图表、性能恶化自动回滚；
5. Qwen‑max 密钥、参数全部从环境变量读取，硬编码零密钥。

## 2.工程目录结构
skill_shop_customer_service/
├── USAGE_GUIDE.md # 使用说明书
├── skill_meta.md # skill 全局元配置、懒加载映射、可进化配置清单
├── bootstrap.py # 动态懒加载管理器
├── requirements.txt # 依赖清单
├── utils/
│ └── config_parser.py # md 配置读写工具：load_md_config /dump_md_config
├── context/
│ └── session_context.py # 会话上下文数据结构
├── intent/
│ ├── intent_config.md # 意图识别配置
│ └── intent_detector.py
├── state_machine/
│ ├── sm_config.md # 状态机流转配置
│ └── state_controller.py
├── rule/
│ ├── rule_config.md # 业务规则配置
│ └── rule_manager.py
├── tool/
│ ├── tool_hook_config.md # 工具 API 钩子配置
│ └── tool_invoker.py
├── reply_template/
│ ├── speech_config.md # 回复话术模板
│ └── speech_engine.py
├── hook/
│ ├── hook_config.md # 后置钩子开关
│ └── post_hook.py
├── self_evolve/
│ ├── evolve_meta.md # 自进化全局参数
│ ├── evolve_collector.py # 会话指标采集器
│ ├── evolve_llm_agent.py # Qwen‑max 优化代理
│ ├── evolve_config_operator.py # md 配置备份、写入、回滚
│ └── evolve_logger.py # 指标计算、日志保存、绘图
├── logs/
│ ├── raw_session/ # 原始会话日志
│ ├── evolve_compare/ # 每轮进化对比日志
│ └── chart/ # 优化前后对比折线 / 柱状图
├── self_evolve/config_backup/ # md 配置备份目录
├── api/
│ └── fastapi_entry.py # HTTP 服务入口
└── docs/
├── extend_slot.md
└── usage_guide.md


## 3.环境变量 .env 参数说明
|环境变量|说明|
|---|---|
|DASHSCOPE_API_KEY|通义千问DashScope密钥|
|QWEN_MODEL_NAME|模型名称，默认 qwen‑max|
|API_HOST|Fastapi监听地址|
|API_PORT|服务端口|
|ENABLE_SELF_EVOLVE|true/false，开启或者关闭自动进化功能|

> 生产环境可以不使用 .env 文件，直接操作系统环境变量注入密钥。

## 4.部署启动步骤
### 4.1 安装依赖
```bash
pip install -r requirements.txt

## 4.2 配置密钥

set DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
set QWEN_MODEL_NAME="qwen-max"
set ENABLE_SELF_EVOLVE="true"
set API_HOST=0.0.0.0
set API_PORT=8000

## 4.3 启动后端接口服务

uvicorn api.fastapi_entry:app --host 0.0.0.0 --port 8000

5. 接口调用方式
请求地址
POST http://127.0.0.1:8000/skill/shop_service/chat