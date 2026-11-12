import numpy as np

def precision_at_k(retrieved_ids: list, ground_ids: set, k: int):
    topk = retrieved_ids[:k]
    hit = len([cid for cid in topk if cid in ground_ids])
    return hit / k if k != 0 else 0

def recall_at_k(retrieved_ids: list, ground_ids: set, k: int):
    topk = retrieved_ids[:k]
    hit = len([cid for cid in topk if cid in ground_ids])
    return hit / len(ground_ids) if len(ground_ids) != 0 else 0

def ndcg_at_k(retrieved_ids: list, ground_ids: set, k: int):
    dcg = 0.0
    idcg = sum(1.0 / np.log2(i+2) for i in range(min(k, len(ground_ids))))
    for idx, cid in enumerate(retrieved_ids[:k]):
        if cid in ground_ids:
            dcg += 1.0 / np.log2(idx + 2)
    return dcg / idcg if idcg != 0 else 0

def mrr(retrieved_ids: list, ground_ids: set):
    for rank, cid in enumerate(retrieved_ids):
        if cid in ground_ids:
            return 1.0 / (rank + 1)
    return 0.0