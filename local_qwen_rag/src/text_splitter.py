import jsonlines
from typing import List, Dict
from src.logger_config import log

class TextSplitter:
    def __init__(self, chunk_size: int, chunk_overlap: int, save_path: str):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.save_path = save_path
        print(f"分块器初始化完成 | chunk_size={chunk_size} overlap={chunk_overlap}")
        print(f"分块持久化文件路径: {save_path}")

    def split_text(self, text: str) -> List[str]:
        chunks = []
        start = 0
        text_len = len(text)
        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            chunk = text[start:end]
            chunks.append(chunk)
            start += self.chunk_size - self.chunk_overlap
        return chunks

    def split_and_save(self, raw_docs: List[Dict]) -> List[Dict]:
        all_chunks = []
        chunk_id = 0
        print(f"\n开始切分 {len(raw_docs)} 份文档并写入本地分块文件")
        # 增量写入
        with jsonlines.open(self.save_path, mode="a") as writer:
            for doc_idx, doc in enumerate(raw_docs):
                print(f"\n[文档进度 {doc_idx+1}/{len(raw_docs)}] 切分 {doc['file_name']}")
                doc_chunks = self.split_text(doc["content"])
                print(f"  该文档生成分块数量: {len(doc_chunks)}")
                for chunk_text in doc_chunks:
                    chunk_item = {
                        "chunk_id": chunk_id,
                        "source_file": doc["file_name"],
                        "doc_id": doc["doc_id"],
                        "chunk_text": chunk_text
                    }
                    writer.write(chunk_item)
                    all_chunks.append(chunk_item)
                    chunk_id += 1
        print(f"\n✅ 全部文档分块结束，总块数: {len(all_chunks)}")
        log.info(f"完成分块，总块数: {len(all_chunks)}，已保存至 {self.save_path}")
        return all_chunks