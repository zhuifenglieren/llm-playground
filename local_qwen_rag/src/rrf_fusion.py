def rrf_fuse(vector_results: list[tuple[float, dict]], bm25_results: list[tuple[float, dict]], k=60):
    """
    RRF融合算法
    vector_results: [(相似度分, chunk)]
    bm25_results: [(bm25分, chunk)]
    return: 融合后排序chunk列表
    """
    rank_dict = {}
    # 向量检索打分
    for rank, (score, chunk) in enumerate(vector_results):
        cid = chunk["chunk_id"]
        rrf_score = 1.0 / (k + rank + 1)
        if cid in rank_dict:
            rank_dict[cid] += rrf_score
        else:
            rank_dict[cid] = rrf_score
    # BM25打分
    for rank, (score, chunk) in enumerate(bm25_results):
        cid = chunk["chunk_id"]
        rrf_score = 1.0 / (k + rank + 1)
        if cid in rank_dict:
            rank_dict[cid] += rrf_score
        else:
            rank_dict[cid] = rrf_score
    # 去重并按RRF分数降序
    chunk_map = {c["chunk_id"]: c for _, c in vector_results + bm25_results}
    sorted_cids = sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)
    fused_chunks = [chunk_map[cid] for cid, score in sorted_cids]
    return fused_chunks