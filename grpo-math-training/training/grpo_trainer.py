import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from typing import Dict, List, Optional
import numpy as np
from tqdm import tqdm
import logging
import os
import gc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GRPOTrainer:
    """GRPO (Group Relative Policy Optimization) 训练器（简化版）"""

    def __init__(self,
                 model,
                 tokenizer,
                 reward_function,
                 learning_rate: float = 1e-5,
                 group_size: int = 4,
                 clip_epsilon: float = 0.2,
                 kl_coef: float = 0.1,
                 max_grad_norm: float = 1.0,
                 device: str = "cuda"):
        """
        初始化GRPO训练器

        Args:
            model: 策略模型
            tokenizer: 分词器
            reward_function: 奖励函数
            learning_rate: 学习率
            group_size: 每组采样数量
            clip_epsilon: PPO裁剪参数
            kl_coef: KL散度系数
            max_grad_norm: 梯度裁剪阈值
            device: 计算设备
        """
        self.model = model
        self.tokenizer = tokenizer
        self.reward_function = reward_function
        self.device = device
        self.group_size = group_size
        self.clip_epsilon = clip_epsilon
        self.kl_coef = kl_coef
        self.max_grad_norm = max_grad_norm

        # 优化器
        self.optimizer = torch.optim.AdamW(
            filter(lambda p: p.requires_grad, model.parameters()),
            lr=learning_rate
        )

        print(f"GRPO训练器初始化完成:")
        print(f"  设备: {self.device}")
        print(f"  组大小: {self.group_size}")
        print(f"  学习率: {learning_rate}")
        print(f"  裁剪参数: {self.clip_epsilon}")
        print(f"  KL系数: {self.kl_coef}")

    def generate_responses(self,
                           prompts: List[str],
                           num_samples: int = 1,
                           max_length: int = 50,
                           temperature: float = 0.8) -> List[str]:
        """
        生成模型响应

        Args:
            prompts: 提示文本列表
            num_samples: 每个提示生成的样本数
            max_length: 最大生成长度
            temperature: 采样温度

        Returns:
            生成的响应列表
        """
        self.model.eval()
        responses = []

        with torch.no_grad():
            for prompt in prompts:
                for _ in range(num_samples):
                    try:
                        # 编码输入
                        inputs = self.tokenizer(
                            prompt,
                            return_tensors="pt",
                            truncation=True,
                            max_length=128,
                            padding=True,
                            add_special_tokens=True
                        )

                        # 移动到设备
                        input_ids = inputs['input_ids'].to(self.device)
                        attention_mask = inputs['attention_mask'].to(self.device)

                        # 验证token ID是否在有效范围内
                        vocab_size = self.model.config.vocab_size
                        if input_ids.max() >= vocab_size:
                            print(f"警告: 输入包含超出词汇表的token ID")
                            input_ids = torch.clamp(input_ids, 0, vocab_size - 1)

                        # 生成响应
                        outputs = self.model.generate(
                            input_ids=input_ids,
                            attention_mask=attention_mask,
                            max_new_tokens=max_length,
                            temperature=temperature,
                            do_sample=True,
                            top_p=0.9,
                            top_k=50,
                            pad_token_id=self.tokenizer.pad_token_id,
                            eos_token_id=self.tokenizer.eos_token_id,
                            use_cache=True,
                            num_return_sequences=1,
                            repetition_penalty=1.1
                        )

                        # 解码响应
                        response = self.tokenizer.decode(
                            outputs[0][input_ids.shape[1]:],
                            skip_special_tokens=True,
                            clean_up_tokenization_spaces=True
                        )
                        responses.append(response)

                    except Exception as e:
                        print(f"生成响应时出错: {e}")
                        responses.append("")

                    # 清理内存
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()

        return responses

    def train_step(self, batch: Dict) -> Dict:
        """
        执行一步训练

        Args:
            batch: 训练批次数据

        Returns:
            训练统计信息
        """
        self.model.train()
        self.optimizer.zero_grad()

        prompts = batch['prompt']
        ground_truths = batch['answer']

        # 生成响应组
        all_responses = []
        all_ground_truths = []

        for prompt, truth in zip(prompts, ground_truths):
            responses = self.generate_responses(
                [prompt],
                num_samples=self.group_size,
                temperature=0.8
            )
            all_responses.extend(responses)
            all_ground_truths.extend([truth] * self.group_size)

        # 计算奖励
        rewards = self.reward_function.compute_batch_rewards(
            all_responses, all_ground_truths
        )

        # 计算优势函数（组内归一化）
        rewards_array = np.array(rewards).reshape(-1, self.group_size)
        advantages = []
        for group_rewards in rewards_array:
            mean_reward = group_rewards.mean()
            std_reward = group_rewards.std() + 1e-8
            group_advantages = (group_rewards - mean_reward) / std_reward
            advantages.extend(group_advantages.tolist())

        advantages = torch.tensor(advantages, device=self.device)

        # 训练循环
        total_loss = 0.0
        valid_samples = 0

        for i, (prompt, response) in enumerate(zip(
                prompts * self.group_size, all_responses
        )):
            if not response:  # 跳过空响应
                continue

            try:
                # 编码完整序列
                full_text = prompt + response
                inputs = self.tokenizer(
                    full_text,
                    return_tensors="pt",
                    truncation=True,
                    max_length=256,
                    padding=True,
                    add_special_tokens=True
                )

                # 移动到设备
                input_ids = inputs['input_ids'].to(self.device)
                attention_mask = inputs['attention_mask'].to(self.device)

                # 验证token ID
                vocab_size = self.model.config.vocab_size
                if input_ids.max() >= vocab_size:
                    input_ids = torch.clamp(input_ids, 0, vocab_size - 1)

                # 前向传播
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask
                )
                logits = outputs.logits

                # 简化的损失计算
                shift_logits = logits[:, :-1, :].contiguous()
                shift_labels = input_ids[:, 1:].contiguous()
                shift_mask = attention_mask[:, 1:].contiguous()

                # 计算交叉熵损失
                loss = F.cross_entropy(
                    shift_logits.view(-1, shift_logits.size(-1)),
                    shift_labels.view(-1),
                    reduction='none'
                )

                # 应用注意力掩码
                loss = loss.view(shift_labels.shape)
                loss = (loss * shift_mask).sum() / (shift_mask.sum() + 1e-8)

                # 应用优势权重（简化的策略梯度）
                weighted_loss = loss * (1.0 - advantages[i].item())
                total_loss += weighted_loss
                valid_samples += 1

                # 反向传播
                weighted_loss.backward()

                # 梯度裁剪
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(), self.max_grad_norm
                )

                # 更新参数
                self.optimizer.step()
                self.optimizer.zero_grad()

                # 清理内存
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            except Exception as e:
                print(f"训练步骤出错: {e}")
                continue

        if valid_samples > 0:
            avg_loss = total_loss / valid_samples
            avg_reward = sum(rewards) / len(rewards) if rewards else 0.0
        else:
            avg_loss = torch.tensor(0.0)
            avg_reward = 0.0

        return {
            "loss": avg_loss.item() if torch.is_tensor(avg_loss) else avg_loss,
            "avg_reward": avg_reward,
            "num_samples": len(all_responses)
        }

    def train(self,
              dataset,
              num_epochs: int = 3,
              batch_size: int = 2,
              save_path: str = "./checkpoints"):
        """
        训练模型

        Args:
            dataset: 训练数据集
            num_epochs: 训练轮数
            batch_size: 批次大小
            save_path: 模型保存路径
        """
        os.makedirs(save_path, exist_ok=True)

        # 限制数据加载器的工作进程数
        dataloader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=0  # 避免多进程问题
        )

        for epoch in range(num_epochs):
            logger.info(f"开始第 {epoch + 1} 轮训练")
            epoch_loss = 0.0
            epoch_reward = 0.0
            num_batches = 0

            progress_bar = tqdm(dataloader, desc=f"Epoch {epoch + 1}")
            for batch in progress_bar:
                stats = self.train_step(batch)
                epoch_loss += stats['loss']
                epoch_reward += stats['avg_reward']
                num_batches += 1

                progress_bar.set_postfix({
                    'loss': f"{stats['loss']:.4f}",
                    'reward': f"{stats['avg_reward']:.3f}"
                })

                # 定期清理内存
                if num_batches % 10 == 0 and torch.cuda.is_available():
                    torch.cuda.empty_cache()

            if num_batches > 0:
                avg_epoch_loss = epoch_loss / num_batches
                avg_epoch_reward = epoch_reward / num_batches

                logger.info(
                    f"Epoch {epoch + 1} 完成: "
                    f"平均损失={avg_epoch_loss:.4f}, "
                    f"平均奖励={avg_epoch_reward:.3f}"
                )
            else:
                logger.warning(f"Epoch {epoch + 1} 没有有效的训练批次")

            # 保存检查点
            checkpoint_path = os.path.join(save_path, f"epoch_{epoch + 1}")
            try:
                self.model.save_pretrained(checkpoint_path)
                self.tokenizer.save_pretrained(checkpoint_path)
                logger.info(f"模型已保存到: {checkpoint_path}")
            except Exception as e:
                logger.error(f"保存检查点时出错: {e}")

            # 清理内存
            if torch.cuda.is_available():
                torch.cuda.empty_cache()