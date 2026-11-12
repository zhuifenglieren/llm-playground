from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class TrainingConfig:
    """训练配置"""
    # 模型配置
    model_name: str = "Qwen/Qwen1.5-0.5B-Chat"
    use_4bit: bool = True  # 使用4bit量化以节省显存
    device: str = "auto"

    # 数据配置
    train_samples: int = 1000
    eval_samples: int = 10
    operations: List[str] = None  # None表示使用默认运算
    num_range: Tuple[int, int] = (1, 100)

    # 训练配置
    learning_rate: float = 1e-5
    num_epochs: int = 3
    batch_size: int = 2
    group_size: int = 4
    clip_epsilon: float = 0.2
    kl_coef: float = 0.1
    max_grad_norm: float = 1.0

    # 生成配置
    max_length: int = 100
    temperature: float = 0.8

    # 奖励配置
    answer_weight: float = 0.7
    format_weight: float = 0.3

    # 保存配置
    save_path: str = "./checkpoints"
    final_model_path: str = "./final_model"

    def __post_init__(self):
        """初始化后处理"""
        if self.operations is None:
            self.operations = ['+', '-']  # 默认使用加减法