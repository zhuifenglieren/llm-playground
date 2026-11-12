# 渐进式 Skill 执行系统 - 使用指南

## 项目概述

本项目实现了一套可渐进执行的 Skill 系统，通过本地 Harness 调度器调用远程 Qwen-max 大模型，
当前内置「天气预报卡片生成」Skill，支持分步执行、断点续跑和状态保存。

## 目录结构
weather-skill-system/
├── src/ # 核心源码（共 4 个文件）
│ ├── harness.py # Skill 执行引擎
│ ├── skills.py # Skill 定义与注册
│ ├── llm_client.py # Qwen-max API 客户端
│ └── utils.py # 工具函数
├── config/
│ └── config.yaml # 配置文件
├── output/ # 输出目录（自动创建）
├── USAGE_GUIDE.md # 本文档
├── requirements.txt # 依赖
└── main.py # 入口程序


## 环境准备

### 1. 安装依赖
```bash
pip install -r requirements.txt

2. 配置 API Key
# Linux / macOS
export DASHSCOPE_API_KEY="your_api_key"

# Windows PowerShell
$env:DASHSCOPE_API_KEY="your_api_key"

快速开始
方式一：完整运行
python main.py