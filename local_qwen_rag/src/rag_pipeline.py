from src.logger_config import log
from src.rrf_fusion import rrf_fuse

class RAGPipeline:
    def __init__(self, embed_model, chroma_store, bm25_retriever, llm, top_k, rrf_k):
        self.embed = embed_model
        self.chroma = chroma_store
        self.bm25 = bm25_retriever
        self.llm = llm
        self.top_k = top_k
        self.rrf_k = rrf_k
        print(f"RAG流水线初始化 | top_k={top_k}, RRF融合k={rrf_k}")

    def retrieve_fuse(self, query: str):
        print(f"\n1.向量检索阶段，查询向量化中...")
        q_emb = self.embed.encode([query])[0]
        vec_res = self.chroma.search(q_emb, self.top_k)
        vec_items = []
        for idx in range(len(vec_res["ids"][0])):
            chunk_id = vec_res["ids"][0][idx]
            text = vec_res["documents"][0][idx]
            meta = vec_res["metadatas"][0][idx]
            score = vec_res["distances"][0][idx]
            chunk = {
                "chunk_id": chunk_id,
                "chunk_text": text,
                "source_file": meta["source_file"]
            }
            vec_items.append((-score, chunk))
        print(f"  向量检索召回 {len(vec_items)} 条结果")
        log.info(f"向量检索获取 {len(vec_items)} 条结果")

        print(f"\n2.BM25关键词检索阶段")
        bm25_items = self.bm25.retrieve(query, self.top_k)
        print(f"  BM25检索召回 {len(bm25_items)} 条结果")
        log.info(f"BM25检索获取 {len(bm25_items)} 条结果")

        print(f"\n3.RRF分数融合重排")
        fused_chunks = rrf_fuse(vec_items, bm25_items, k=self.rrf_k)
        print(f"  融合后有效文本片段总数: {len(fused_chunks)}")
        log.info(f"RRF融合后有效块数: {len(fused_chunks)}")
        return fused_chunks

    def build_context(self, chunks: list):
        print(f"\n4.拼接检索上下文，片段数量: {len(chunks)}")
        context = ""
        for idx, ck in enumerate(chunks):
            context += f"【片段{idx+1}，来源文件：{ck['source_file']}】\n{ck['chunk_text']}\n\n"
        print(f"  拼接后上下文总长度: {len(context)}")
        return context

    def run_rag(self, query: str):
        print(f"\n========== RAG全链路开始处理提问 ==========")
        log.info(f"===== 开始处理用户提问：{query} =====")
        fuse_chunks = self.retrieve_fuse(query)
        ctx = self.build_context(fuse_chunks)
        print(f"\n5.送入Qwen2本地模型生成回答...")
        answer = self.llm.generate_answer(query, ctx)
        print(f"\n========== RAG流程执行完毕 ==========\n")
        log.info(f"===== 问答结束，返回答案 =====")
        return {
            "query": query,
            "retrieve_chunks": fuse_chunks,
            "context": ctx,
            "answer": answer
        }