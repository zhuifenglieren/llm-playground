from rank_bm25 import BM25Okapi
import jieba
from src.logger_config import log

class BM25Retriever:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.corpus_texts = [item["chunk_text"] for item in chunks]
        self.tokenized_corpus = [jieba.lcut(text) for text in self.corpus_texts]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        log.info(f"BM25索引构建完成，文档块总数: {len(self.chunks)}")

    def retrieve(self, query: str, top_k: int):
        token_query = jieba.lcut(query)
        scores = self.bm25.get_scores(token_query)
        # 构造 (score, chunk_item)
        scored_items = list(zip(scores, self.chunks))
        scored_items.sort(key=lambda x: x[0], reverse=True)
        return scored_items[:top_k]