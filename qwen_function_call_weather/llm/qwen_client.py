import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from config.settings import LOCAL_MODEL_PATH

class QwenLocalClient:
    def __init__(self):
        print(f"[LLM] 开始加载本地模型：{LOCAL_MODEL_PATH}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            LOCAL_MODEL_PATH, trust_remote_code=True
        )
        print(f"[LLM] Tokenizer 加载完成")
        self.model = AutoModelForCausalLM.from_pretrained(
            LOCAL_MODEL_PATH,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )
        self.model.eval()
        print(f"[LLM] 模型加载完毕，推理设备：{self.model.device}")

    def chat(self, messages: list, stream=False):
        """
        messages格式示例：
        [
            {"role": "system", "content": "系统提示词"},
            {"role": "user", "content": "用户问题"}
        ]
        """
        print(f"[LLM] 开始拼接对话模板，消息总数：{len(messages)}")
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        input_token_num = model_inputs["input_ids"].shape[-1]
        print(f"[LLM] 输入token长度：{input_token_num}")

        print(f"[LLM] 执行模型推理生成回答...")
        with torch.no_grad():
            outputs = self.model.generate(
                **model_inputs,
                max_new_tokens=512,
                temperature=0.01,
                top_p=0.7
            )
        output_text = self.tokenizer.decode(outputs[0][len(model_inputs["input_ids"][0]):], skip_special_tokens=True)
        print(f"[LLM] 推理完成，原始输出长度：{len(output_text)} 字符")
        return output_text