import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Tuple, Optional


class ModelLoader:
    """模型加载器，负责加载和管理模型"""

    def __init__(self, model_name: str = "Qwen/Qwen1.5-0.5B-Chat",
                 device: str = "auto"):
        """
        初始化模型加载器

        Args:
            model_name: 模型名称或路径
            device: 设备类型 ('auto', 'cuda', 'cpu')
        """
        self.model_name = model_name
        self.device = self._select_device(device)
        self.model = None
        self.tokenizer = None

    def _select_device(self, device: str) -> str:
        """选择计算设备"""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            else:
                return "cpu"
        return device

    def load_model(self, use_4bit: bool = True) -> Tuple:
        """
        加载模型（支持4bit量化以节省显存）

        Args:
            use_4bit: 是否使用4bit量化

        Returns:
            model, tokenizer
        """
        print(f"正在加载模型: {self.model_name}")
        print(f"使用设备: {self.device}")

        # 加载tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            padding_side="left",
            use_fast=False  # 使用慢速tokenizer避免一些问题
        )

        # 确保tokenizer有正确的特殊token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        if self.tokenizer.bos_token is None:
            self.tokenizer.bos_token = "<|im_start|>"
        if self.tokenizer.eos_token is None:
            self.tokenizer.eos_token = "<|im_end|>"

        print(f"Tokenizer词汇表大小: {len(self.tokenizer)}")
        print(f"Pad token: {self.tokenizer.pad_token} (ID: {self.tokenizer.pad_token_id})")
        print(f"EOS token: {self.tokenizer.eos_token} (ID: {self.tokenizer.eos_token_id})")

        # 加载模型
        if use_4bit and self.device == "cuda":
            # 使用4bit量化加载以节省显存
            try:
                from transformers import BitsAndBytesConfig

                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )

                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    quantization_config=quantization_config,
                    device_map="auto",
                    trust_remote_code=True,
                    torch_dtype=torch.float16
                )
                print("使用4bit量化加载模型")
            except Exception as e:
                print(f"4bit量化加载失败: {e}")
                print("尝试常规加载...")
                use_4bit = False

        if not use_4bit or self.device != "cuda":
            # 常规加载
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True
            )
            if self.device == "cuda":
                self.model = self.model.to(self.device)

        # 确保模型和tokenizer的词汇表大小一致
        model_vocab_size = self.model.config.vocab_size
        tokenizer_vocab_size = len(self.tokenizer)
        print(f"模型词汇表大小: {model_vocab_size}")

        if model_vocab_size != tokenizer_vocab_size:
            print(f"警告: 模型词汇表({model_vocab_size})和tokenizer词汇表({tokenizer_vocab_size})不匹配")
            # 调整模型的embedding层大小
            self.model.resize_token_embeddings(tokenizer_vocab_size)
            print("已调整模型embedding层大小")

        print(f"模型加载完成，设备: {self.device}")
        return self.model, self.tokenizer

    def get_model_info(self) -> dict:
        """获取模型信息"""
        if self.model:
            params = sum(p.numel() for p in self.model.parameters())
            trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
            return {
                "model_name": self.model_name,
                "device": self.device,
                "total_params": params,
                "trainable_params": trainable_params,
                "model_size_mb": params * 4 / 1024 / 1024  # 估算大小
            }
        return None