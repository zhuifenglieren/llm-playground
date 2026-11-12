import random
from typing import List, Dict, Tuple
from datasets import Dataset
import json


class MathDataset:
    """数学题目数据集生成器"""

    def __init__(self, seed: int = 42):
        """
        初始化数学数据集

        Args:
            seed: 随机种子
        """
        random.seed(seed)
        self.operations = ['+', '-', '*', '/']

    def generate_arithmetic_question(self,
                                     num_range: Tuple[int, int] = (1, 100),
                                     operations: List[str] = None) -> Dict:
        """
        生成一道算术题

        Args:
            num_range: 数字范围
            operations: 允许的运算类型

        Returns:
            {"question": 题目, "answer": 答案}
        """
        if operations is None:
            operations = ['+', '-']  # 默认只使用加减法，避免除法复杂性

        op = random.choice(operations)

        if op == '+':
            a = random.randint(*num_range)
            b = random.randint(*num_range)
            question = f"{a} + {b} = ?"
            answer = a + b

        elif op == '-':
            a = random.randint(*num_range)
            b = random.randint(1, a)  # 确保结果非负
            question = f"{a} - {b} = ?"
            answer = a - b

        elif op == '*':
            a = random.randint(1, 20)  # 限制乘数范围
            b = random.randint(1, 20)
            question = f"{a} × {b} = ?"
            answer = a * b

        elif op == '/':
            b = random.randint(1, 20)
            answer = random.randint(1, 20)
            a = b * answer  # 确保整除
            question = f"{a} ÷ {b} = ?"

        return {
            "question": question,
            "answer": str(answer),
            "formatted_answer": f"Answer: {answer}"
        }

    def generate_dataset(self,
                         num_samples: int,
                         operations: List[str] = None,
                         num_range: Tuple[int, int] = (1, 100)) -> Dataset:
        """
        生成训练数据集

        Args:
            num_samples: 样本数量
            operations: 运算类型列表
            num_range: 数字范围

        Returns:
            HuggingFace Dataset
        """
        data = []
        for _ in range(num_samples):
            qa_pair = self.generate_arithmetic_question(num_range, operations)
            data.append({
                "prompt": f"请计算：{qa_pair['question']}\n请以'Answer: '开头回答。",
                "question": qa_pair['question'],
                "answer": qa_pair['answer'],
                "formatted_answer": qa_pair['formatted_answer']
            })

        return Dataset.from_list(data)

    def create_evaluation_set(self, num_samples: int = 10) -> List[Dict]:
        """
        创建评估集

        Args:
            num_samples: 样本数量

        Returns:
            评估数据列表
        """
        eval_data = []
        for _ in range(num_samples):
            qa_pair = self.generate_arithmetic_question()
            eval_data.append({
                "question": qa_pair['question'],
                "answer": qa_pair['answer'],
                "formatted_answer": qa_pair['formatted_answer'],
                "prompt": f"请计算：{qa_pair['question']}\n请以'Answer: '开头回答。"
            })
        return eval_data