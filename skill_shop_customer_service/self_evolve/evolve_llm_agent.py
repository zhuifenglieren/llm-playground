import os
import re
import json
from typing import List, Dict
import dashscope

# 读取命令行设置的系统环境变量
dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY")
QWEN_MODEL = os.environ.get("QWEN_MODEL_NAME", "qwen-max")


class EvolveAgent:
    def __init__(self):
        if not dashscope.api_key:
            raise RuntimeError("环境变量 DASHSCOPE_API_KEY 未通过命令行进行配置")

    def build_prompt(self, sample_list: List[Dict], old_config: Dict[str, str]):
        prompt = """
你是客服技能的自动优化引擎。
优化目标：
1、降低整体输入输出token消耗；
2、降低接口响应耗时；
3、提高意图识别正确率；
4、减少用户负面情绪。
禁止大幅度改动原有业务逻辑。
会话指标样本：
%s
现有全部配置文件内容：
%s
输出严格返回JSON数组，每一项字段 target_file、optimize_reason、new_content。
target_file使用.md后缀路径，new_content填写完整json字符串。
        """ % (json.dumps(sample_list, ensure_ascii=False),
               json.dumps(old_config, ensure_ascii=False))
        return prompt

    async def qwen_max_invoke(self, prompt: str) -> str:
        resp = dashscope.Generation.call(
            model=QWEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            result_format="message"
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Qwen‑max 请求失败:{resp.message}")
        return resp.output.choices[0].message.content

    async def analyse(self, samples, old_config_dict):
        prompt = self.build_prompt(samples, old_config_dict)
        resp_text = await self.qwen_max_invoke(prompt)
        match = re.search(r"\[.*\]", resp_text, re.DOTALL)
        if not match:
            return []
        return json.loads(match.group())


def get_instance():
    return EvolveAgent()