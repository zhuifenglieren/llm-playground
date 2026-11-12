import re
from typing import Dict


class MathReward:
    """数学题目奖励函数"""

    def __init__(self,
                 answer_weight: float = 0.7,
                 format_weight: float = 0.3):
        """
        初始化奖励函数

        Args:
            answer_weight: 答案正确性的权重
            format_weight: 格式正确性的权重
        """
        self.answer_weight = answer_weight
        self.format_weight = format_weight

    def extract_answer(self, response: str) -> str:
        """
        从模型响应中提取答案

        Args:
            response: 模型响应文本

        Returns:
            提取的答案
        """
        # 尝试匹配 "Answer: XXX" 格式
        pattern = r'Answer:\s*([-\d]+)'
        match = re.search(pattern, response, re.IGNORECASE)

        if match:
            return match.group(1)

        # 尝试匹配最后一个数字
        numbers = re.findall(r'-?\d+', response)
        if numbers:
            return numbers[-1]

        return ""

    def check_format(self, response: str) -> bool:
        """
        检查响应格式是否正确

        Args:
            response: 模型响应文本

        Returns:
            格式是否正确
        """
        pattern = r'Answer:\s*[-\d]+'
        return bool(re.search(pattern, response, re.IGNORECASE))

    def compute_reward(self,
                       response: str,
                       ground_truth: str) -> float:
        """
        计算奖励值

        Args:
            response: 模型响应
            ground_truth: 正确答案

        Returns:
            奖励值 [0, 1]
        """
        # 提取答案
        extracted_answer = self.extract_answer(response)

        # 检查格式
        format_correct = self.check_format(response)

        # 检查答案正确性
        answer_correct = (extracted_answer == ground_truth)

        # 计算加权奖励
        reward = 0.0
        if answer_correct:
            reward += self.answer_weight
        if format_correct:
            reward += self.format_weight

        # 如果答案正确但格式错误，给予部分奖励
        if answer_correct and not format_correct:
            reward = max(reward, 0.5)

        return reward

    def compute_batch_rewards(self,
                              responses: list,
                              ground_truths: list) -> list:
        """
        批量计算奖励

        Args:
            responses: 模型响应列表
            ground_truths: 正确答案列表

        Returns:
            奖励值列表
        """
        rewards = []
        for response, truth in zip(responses, ground_truths):
            reward = self.compute_reward(response, truth)
            rewards.append(reward)
        return rewards