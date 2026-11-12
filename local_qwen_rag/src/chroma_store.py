import chromadb
from src.logger_config import log

class ChromaVectorStore:
    def __init__(self, persist_path: str, coll_name: str):
        self.client = chromadb.PersistentClient(path=persist_path)
        self.collection = self.client.get_or_create_collection(name=coll_name)
        log.info(f"ChromaDB初始化完成，集合名: {coll_name}")

    def add_chunks(self, chunk_ids: list[str], texts: list[str], embeddings, metadatas: list[dict]):
        self.collection.add(
            ids=chunk_ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )
        log.info(f"向量库新增 {len(chunk_ids)} 条向量")

    def search(self, query_embedding, top_k: int):
        res = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        return res