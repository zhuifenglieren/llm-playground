import os

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from src.logger_config import log


class Qwen2LocalLLM:
    def __init__(self, model_path: str, device: str, temperature=0.1, max_new_tokens=1024):
        self.device = torch.device(device)
        self.temp = temperature
        self.max_new = max_new_tokens
        print(f"[LLM] 离线加载路径：{model_path}")

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            local_files_only=True,
            trust_remote_code=True
        )
        # 无需use_safetensors，仓库自带pytorch_model.bin
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float32,
            device_map=device,
            local_files_only=True,
            trust_remote_code=True
        )
        print("[LLM] 模型加载完成")

    def generate_answer(self, query: str, context: str):
        prompt = f"""基于以下参考上下文回答用户问题，答案仅来自上下文，禁止编造：
【参考上下文】
{context}
【用户问题】
{query}
回答："""
        messages = [{"role": "user", "content": prompt}]
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer([text], return_tensors="pt").to(self.device)

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=self.max_new,
            temperature=self.temp,
            do_sample=True
        )
        resp = self.tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)
        return resp