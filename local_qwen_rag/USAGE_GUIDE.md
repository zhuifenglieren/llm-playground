# 本地Qwen2 RAG智能问答系统使用手册
## 项目简介
基于PDF本地知识库，实现「向量检索+BM25关键词检索+RRF分数融合」混合检索RAG，
使用本地Qwen2-0.5B-Instruct大模型生成答案，配套完整检索/生成评估体系，全流程日志落地，文档分块持久化存储。

##1. 项目结构
local_qwen_rag/
├── USAGE_GUIDE.md              # 完整使用文档
├── requirements.txt            # 依赖清单
├── config.yaml                 # 全局配置文件（分块、模型、向量库、评估参数）
├── main.py                     # 程序入口
├── run_eval.py                 # 评估脚本
├── logs/                       # 全流程日志目录
│   ├── rag_runtime.log         # 检索+生成运行日志
│   └── eval_result.log         # 评估指标日志
├── data/                       # 原始知识库与分块存储
│   ├── raw_pdf/                # 存放用户上传PDF原始文件
│   └── split_chunks/           # 持久化保存所有文档切分后的文本块(json存储)
├── vector_store/               # ChromaDB向量数据库持久化目录
├── src/                        # 核心业务模块
│   ├── __init__.py
│   ├── pdf_loader.py           # PDF加载、文本清洗
│   ├── text_splitter.py        # 文档分块，块本地持久化
│   ├── embedding_model.py      # 本地向量化模型封装
│   ├── chroma_store.py         # Chroma向量库增删查
│   ├── bm25_retriever.py       # BM25关键词检索模块
│   ├── rrf_fusion.py           # RRF融合算法实现
│   ├── llm_qwen2.py            # 本地Qwen2-0.5B-Instruct推理封装
│   ├── rag_pipeline.py         # 完整RAG链路（检索融合+上下文组装+大模型生成）
│   ├── logger_config.py        # 全局日志统一配置
│   └── evaluator/              # 检索+生成双维度评估模块
│       ├── __init__.py
│       ├── retrieval_metric.py  # 检索指标：Precision@k、Recall@k、NDCG、MRR
│       └── generation_metric.py# 生成指标：BLEU、ROUGE、相似度、LLM打分
└── test_dataset/               # 评估测试集（question/answer/标准检索文档）
    └── test_qa.json
##2 环境部署
##2.1 安装依赖
```bash
pip install -r requirements.txt

##2.2 下载模型
```bash
python download_models.py

##2.3 使用说明

步骤 1：构建知识库（加载 PDF→分块→保存分块文件→入库 Chroma + 构建 BM25 索引）
python main.py --build
步骤 2：交互式问答
python main.py --chat
步骤 3：全链路效果评估
python run_eval.py
