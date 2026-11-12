import warnings
# 屏蔽jieba废弃警告
warnings.filterwarnings("ignore", category=UserWarning, module="jieba._compat")

import argparse
import os
import yaml
from src.logger_config import log
from src.pdf_loader import load_all_pdf
from src.text_splitter import TextSplitter
from src.embedding_model import LocalEmbedding
from src.chroma_store import ChromaVectorStore
from src.bm25_retriever import BM25Retriever
from src.rag_pipeline import RAGPipeline
from src.llm_qwen2 import Qwen2LocalLLM

# 加载配置
print("="*60)
print("【步骤0】加载全局配置文件 config.yaml")
with open("config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)
print("✅ 配置加载完成")
print("="*60)

# 创建文件夹
dirs = ["data/raw_pdf", "data/split_chunks", "vector_store", "logs", "models", "test_dataset"]
print("【步骤0】初始化项目文件夹")
for d in dirs:
    os.makedirs(d, exist_ok=True)
    print(f"  已确保目录存在: {d}")
print("✅ 文件夹初始化完毕")
print("="*60)

def build_knowledge_base():
    print("\n========== 开始构建知识库 ==========")
    # 1.加载PDF
    print("【步骤1】读取raw_pdf目录下所有PDF文档")
    raw_docs = load_all_pdf("data/raw_pdf")
    if not raw_docs:
        print("❌ 未读取到任何有效PDF文档，终止构建流程")
        log.error("未读取到任何PDF文档，终止构建")
        return
    print(f"✅ 共加载到 {len(raw_docs)} 份PDF文档")
    for doc in raw_docs:
        print(f"  - Doc{doc['doc_id']}: {doc['file_name']} | 文本长度: {len(doc['content'])}")
    print("-"*50)

    # 2.分块并保存块文件
    print("【步骤2】初始化文本分块器，执行文档切分")
    splitter = TextSplitter(
        cfg["split"]["chunk_size"],
        cfg["split"]["chunk_overlap"],
        cfg["split"]["chunk_save_path"]
    )
    print(f"  分块参数 chunk_size={cfg['split']['chunk_size']}, overlap={cfg['split']['chunk_overlap']}")
    all_chunks = splitter.split_and_save(raw_docs)
    print(f"✅ 文档切分完成，总生成文本块数量: {len(all_chunks)}")
    print(f"  分块文件持久化路径: {cfg['split']['chunk_save_path']}")
    print("-"*50)

    chunk_texts = [c["chunk_text"] for c in all_chunks]
    chunk_ids = [str(c["chunk_id"]) for c in all_chunks]
    metas = [{"source_file": c["source_file"]} for c in all_chunks]

    # 3.向量化
    print("【步骤3】加载本地Embedding模型，开始批量向量化文本块")
    embed = LocalEmbedding(cfg["embedding"]["model_name"], cfg["embedding"]["device"])
    print(f"  向量模型: {cfg['embedding']['model_name']} | 运行设备: {cfg['embedding']['device']}")
    print("  正在编码全部文本块，耗时取决于块数量...")
    vectors = embed.encode(chunk_texts)
    print(f"✅ 向量化完成，向量维度: {len(vectors[0])}")
    print("-"*50)

    # 4.写入Chroma向量库
    print("【步骤4】初始化ChromaDB持久化向量库，写入向量数据")
    chroma = ChromaVectorStore(cfg["chroma"]["persist_path"], cfg["chroma"]["collection_name"])
    chroma.add_chunks(chunk_ids, chunk_texts, vectors, metas)
    print(f"✅ 向量库写入完成，持久化目录: {cfg['chroma']['persist_path']}")
    print("\n========== 知识库全流程构建完毕 ==========")

def chat_loop():
    print("\n========== 初始化问答交互环境 ==========")
    # 加载嵌入模型
    print("【初始化1】加载Embedding模型")
    embed = LocalEmbedding(cfg["embedding"]["model_name"], cfg["embedding"]["device"])
    print("✅ Embedding加载完成")

    # 加载向量库
    print("【初始化2】连接本地Chroma向量库")
    chroma = ChromaVectorStore(cfg["chroma"]["persist_path"], cfg["chroma"]["collection_name"])
    print("✅ ChromaDB连接成功")

    # 读取分块构建BM25
    print("【初始化3】读取本地保存的分块文件，构建BM25检索索引")
    import jsonlines
    all_chunks = []
    chunk_save_path = cfg["split"]["chunk_save_path"]
    if not os.path.exists(chunk_save_path):
        print(f"❌ 分块文件不存在 {chunk_save_path}，请先执行 --build 构建知识库")
        return
    with jsonlines.open(chunk_save_path, "r") as r:
        for item in r:
            all_chunks.append(item)
    print(f"  读取到历史分块总数: {len(all_chunks)}")
    bm25 = BM25Retriever(all_chunks)
    print("✅ BM25稀疏检索索引构建完成")

    # 加载Qwen大模型
    print("【初始化4】加载本地Qwen2-0.5B-Instruct大模型")
    llm = Qwen2LocalLLM(
        cfg["llm"]["model_path"], cfg["llm"]["device"],
        cfg["llm"]["temperature"], cfg["llm"]["max_new_tokens"]
    )
    print("✅ Qwen2大模型加载完成")

    # 组装RAG流水线
    print("【初始化5】组装混合检索RAG流水线（向量+BM25+RRF融合）")
    rag = RAGPipeline(embed, chroma, bm25, llm, cfg["retrieval"]["top_k"], cfg["retrieval"]["rrf_k"])
    print("✅ RAG流水线就绪，可以开始问答！")
    print("="*60)
    print("输入问题进行问答，输入 exit 退出程序")
    print("="*60)

    while True:
        q = input("\n请输入问题：")
        if q.strip().lower() == "exit":
            print("程序正常退出")
            break
        print(f"\n[用户提问] {q}")
        print("------ 开始执行检索融合 ------")
        res = rag.run_rag(q)
        print("------ 检索与生成完成 ------")
        print(f"\n【检索召回片段数量】{len(res['retrieve_chunks'])}")
        print("\n【回答】")
        print(res['answer'])
        print("-"*80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="构建PDF知识库")
    parser.add_argument("--chat", action="store_true", help="开启交互式问答")
    args = parser.parse_args()
    if args.build:
        build_knowledge_base()
    elif args.chat:
        chat_loop()
    else:
        print("参数错误，请选择：")
        print("  python main.py --build    构建知识库")
        print("  python main.py --chat     启动问答交互")