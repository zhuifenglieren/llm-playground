import torch
from typing import List, Dict
import re
from tqdm import tqdm


class Evaluator:
    """模型评估器"""

    def __init__(self, model, tokenizer, reward_function, device: str = "cuda"):
        """
        初始化评估器

        Args:
            model: 待评估模型
            tokenizer: 分词器
            reward_function: 奖励函数
            device: 计算设备
        """
        self.model = model
        self.tokenizer = tokenizer
        self.reward_function = reward_function
        self.device = device

    def evaluate(self,
                 eval_data: List[Dict],
                 max_length: int = 100) -> Dict:
        """
        评估模型性能

        Args:
            eval_data: 评估数据
            max_length: 最大生成长度

        Returns:
            评估结果
        """
        self.model.eval()

        correct_answers = 0
        correct_format = 0
        total_reward = 0.0
        results = []

        print("\n开始评估模型性能...")
        for item in tqdm(eval_data, desc="评估进度"):
            prompt = item['prompt']
            ground_truth = item['answer']

            # 生成响应
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=256
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    temperature=0.1,  # 低温度以获得更确定的输出
                    do_sample=False,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )

            response = self.tokenizer.decode(
                outputs[0][inputs['input_ids'].shape[1]:],
                skip_special_tokens=True
            )

            # 计算奖励
            reward = self.reward_function.compute_reward(response, ground_truth)
            total_reward += reward

            # 检查正确性
            extracted_answer = self.reward_function.extract_answer(response)
            is_correct = (extracted_answer == ground_truth)
            is_formatted = self.reward_function.check_format(response)

            if is_correct:
                correct_answers += 1
            if is_formatted:
                correct_format += 1

            results.append({
                "question": item['question'],
                "ground_truth": ground_truth,
                "model_response": response,
                "extracted_answer": extracted_answer,
                "is_correct": is_correct,
                "is_formatted": is_formatted,
                "reward": reward
            })

        # 计算统计信息
        total_samples = len(eval_data)
        accuracy = correct_answers / total_samples
        format_accuracy = correct_format / total_samples
        avg_reward = total_reward / total_samples

        return {
            "total_samples": total_samples,
            "accuracy": accuracy,
            "format_accuracy": format_accuracy,
            "avg_reward": avg_reward,
            "correct_answers": correct_answers,
            "correct_format": correct_format,
            "results": results
        }

    def print_results(self, evaluation_results: Dict, title: str = "评估结果"):
        """
        打印评估结果

        Args:
            evaluation_results: 评估结果字典
            title: 标题
        """
        print(f"\n{'=' * 50}")
        print(f"{title}")
        print(f"{'=' * 50}")
        print(f"总样本数: {evaluation_results['total_samples']}")
        print(f"答案准确率: {evaluation_results['accuracy']:.2%}")
        print(f"格式准确率: {evaluation_results['format_accuracy']:.2%}")
        print(f"平均奖励: {evaluation_results['avg_reward']:.3f}")
        print(f"正确答案数: {evaluation_results['correct_answers']}")
        print(f"格式正确数: {evaluation_results['correct_format']}")

        # 打印详细结果
        print(f"\n详细结果:")
        for i, result in enumerate(evaluation_results['results'], 1):
            print(f"\n题目 {i}: {result['question']}")
            print(f"正确答案: {result['ground_truth']}")
            print(f"模型回答: {result['model_response'][:100]}")
            print(f"提取答案: {result['extracted_answer']}")
            print(f"是否正确: {'✓' if result['is_correct'] else '✗'}")
            print(f"格式正确: {'✓' if result['is_formatted'] else '✗'}")
            print(f"奖励值: {result['reward']:.3f}")
        print(f"\n{'=' * 50}\n")