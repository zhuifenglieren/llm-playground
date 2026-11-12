import json
import yaml
from src.logger_config import log
from src.rag_pipeline import RAGPipeline
from src.evaluator.retrieval_metric import precision_at_k, recall_at_k, ndcg_at_k, mrr
from src.evaluator.generation_metric import calc_rouge, calc_bleu
from src.embedding_model import LocalEmbedding
from src.chroma_store import ChromaVectorStore
from src.bm25_retriever import BM25Retriever
from src.llm_qwen2 import Qwen2LocalLLM

with open("config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

# 初始化所有模块
embed = LocalEmbedding(cfg["embedding"]["model_name"], cfg["embedding"]["device"])
chroma = ChromaVectorStore(cfg["chroma"]["persist_path"], cfg["chroma"]["collection_name"])
# 读取全部分块
import jsonlines
all_chunks = []
with jsonlines.open(cfg["split"]["chunk_save_path"], "r") as r:
    for item in r:
        all_chunks.append(item)
bm25 = BM25Retriever(all_chunks)
llm = Qwen2LocalLLM(
    cfg["llm"]["model_path"], cfg["llm"]["device"],
    cfg["llm"]["temperature"], cfg["llm"]["max_new_tokens"]
)
rag = RAGPipeline(embed, chroma, bm25, llm, cfg["retrieval"]["top_k"], cfg["retrieval"]["rrf_k"])

# 加载测试集
with open(cfg["eval"]["test_data_path"], "r", encoding="utf-8") as f:
    test_data = json.load(f)

top_k_list = cfg["eval"]["top_k_list"]
total_metrics = {
    "p@k": {k: [] for k in top_k_list},
    "r@k": {k: [] for k in top_k_list},
    "ndcg@k": {k: [] for k in top_k_list},
    "mrr": [],
    "rouge1": [], "rouge2": [], "rougeL": [], "bleu": []
}

for sample in test_data:
    q = sample["question"]
    ref_ans = sample["answer"]
    ground_chunk_ids = set(sample["ground_chunk_ids"])
    res = rag.run_rag(q)
    pred_ans = res["answer"]
    retrieved_cids = [ck["chunk_id"] for ck in res["retrieve_chunks"]]

    # 检索指标
    for k in top_k_list:
        total_metrics["p@k"][k].append(precision_at_k(retrieved_cids, ground_chunk_ids, k))
        total_metrics["r@k"][k].append(recall_at_k(retrieved_cids, ground_chunk_ids, k))
        total_metrics["ndcg@k"][k].append(ndcg_at_k(retrieved_cids, ground_chunk_ids, k))
    total_metrics["mrr"].append(mrr(retrieved_cids, ground_chunk_ids))

    # 生成指标
    rouge = calc_rouge(pred_ans, ref_ans)
    bleu = calc_bleu(pred_ans, ref_ans)
    total_metrics["rouge1"].append(rouge["rouge1_f"])
    total_metrics["rouge2"].append(rouge["rouge2_f"])
    total_metrics["rougeL"].append(rouge["rougeL_f"])
    total_metrics["bleu"].append(bleu)

# 汇总输出
log_extra = log.bind(EVAL="True")
log_extra.info("======= 整体评估均值结果 =======")
for k in top_k_list:
    log_extra.info(f"P@{k}: {sum(total_metrics['p@k'][k])/len(test_data):.4f}")
    log_extra.info(f"R@{k}: {sum(total_metrics['r@k'][k])/len(test_data):.4f}")
    log_extra.info(f"NDCG@{k}: {sum(total_metrics['ndcg@k'][k])/len(test_data):.4f}")
log_extra.info(f"MRR均值: {sum(total_metrics['mrr'])/len(test_data):.4f}")
log_extra.info(f"ROUGE1均值: {sum(total_metrics['rouge1'])/len(test_data):.4f}")
log_extra.info(f"ROUGE2均值: {sum(total_metrics['rouge2'])/len(test_data):.4f}")
log_extra.info(f"ROUGEL均值: {sum(total_metrics['rougeL'])/len(test_data):.4f}")
log_extra.info(f"BLEU均值: {sum(total_metrics['bleu'])/len(test_data):.4f}")