import os
# 只保留纯离线开关，删掉HF_ENDPOINT避免离线时触发镜像域名检查
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

from sentence_transformers import SentenceTransformer
import torch
from src.logger_config import log

class LocalEmbedding:
    def __init__(self, model_name: str, device: str):
        self.device = torch.device(device)
        log.info(f"离线加载向量模型相对路径: {model_name}")
        print(f"[Embedding] 离线加载模型：{model_name}")
        self.model = SentenceTransformer(
            model_name,
            device=self.device,
            #local_files_only=True
        )
        print("[Embedding] 向量模型加载成功")

    def encode(self, texts: list[str]) -> list[list[float]]:
        print(f"[Embedding] 开始编码 {len(texts)} 条文本")
        embeddings = self.model.encode(texts, convert_to_tensor=False)
        print("[Embedding] 向量化完成")
        return embeddings.tolist()