"""
Function Calling API 版 ReAct Agent（支持多轮长短记忆）
"""
import os
import json
import time
import logging
import argparse
from typing import Generator
from memory import get_session_messages, append_session_msg, recall_long_memory

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
MODEL = os.getenv("AGENT_MODEL", "qwen-max")

BASE_FC_PROMPT = """你是专业A股金融分析助手，规则：
1. 调用financial_indicator/stock_price前必须先用company_lookup查股票代码
2. 所有数值计算使用calculator，禁止心算
3. Final Answer必须标注数据来源
4. 参考历史对话记忆，不要重复查询已获取数据
5. 无工具可解答则直接说明限制
"""

def run(question: str, session_id: str, max_steps: int = 10) -> Generator[dict, None, None]:
    from tools import TOOLS_MAP, TOOLS_SCHEMA
    history_mem = recall_long_memory(question)
    sys_prompt = BASE_FC_PROMPT
    if history_mem:
        sys_prompt += "\n【历史对话参考】\n" + "\n".join(history_mem)

    # 持久记忆只存用户提问和最终回答，不含工具中间流程
    messages = get_session_messages(session_id)
    if not messages:
        messages.append({"role": "system", "content": sys_prompt})
    user_msg = {"role": "user", "content": question}
    append_session_msg(session_id, user_msg)
    messages.append(user_msg)

    for step in range(1, max_steps + 1):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            temperature=0,
        )
        msg = response.choices[0].message
        reason = response.choices[0].finish_reason

        # 直接给出最终答案，终止循环
        if reason == "stop" or not msg.tool_calls:
            yield {
                "step": step,
                "type": "final",
                "thought": "",
                "answer": msg.content or "（模型返回空内容）",
            }
            append_session_msg(session_id, {"role": "assistant", "content": msg.content})
            return

        # 一次只处理单个tool_call，拆分循环保证消息顺序合法
        for tool_call in msg.tool_calls:
            # 1. 先插入本次带工具调用的assistant消息（必须放在tool前面）
            assistant_dict = {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [tool_call.model_dump()]
            }
            messages.append(assistant_dict)

            # 2. 执行单工具
            tool_name = tool_call.function.name
            try:
                tool_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                tool_args = {}
            tool_fn = TOOLS_MAP.get(tool_name)
            if tool_fn is None:
                observation = f"未知工具 '{tool_name}'"
            else:
                try:
                    observation = tool_fn(**tool_args)
                except TypeError as e:
                    observation = f"工具参数错误: {e}"

            step_result = {
                "step": step,
                "type": "action",
                "thought": "",
                "action": tool_name,
                "action_input": tool_args,
                "observation": str(observation),
            }
            yield step_result

            # 3. 插入对应tool回复，一一配对
            tool_msg = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(observation),
            }
            messages.append(tool_msg)

    yield {
        "step": max_steps + 1,
        "type": "max_steps",
        "answer": f"已达最大步数 {max_steps}，未能得出最终答案",
    }

# CLI打印
COLORS = {
    "thought": "\033[36m", "action":  "\033[33m", "obs":     "\033[32m",
    "final":   "\033[35m", "error":   "\033[31m", "reset":   "\033[0m",
}
def _c(color: str, text: str) -> str:
    return f"{COLORS[color]}{text}{COLORS['reset']}"

def run_and_print(question: str, session_id: str, max_steps: int = 10):
    print(f"\n{'='*60}")
    print(f"问题: {question} | 会话ID:{session_id}")
    print(f"模型: {MODEL}  实现: Function Calling（多轮记忆）")
    print('='*60)
    start = time.time()
    for step_data in run(question, session_id, max_steps=max_steps):
        stype = step_data["type"]
        if stype == "action":
            print(f"\n[Step {step_data['step']}]")
            print(_c("thought", "🧠 Thought: （模型内部推理，FC版不可见）"))
            print(_c("action",  f"🔧 Action:  {step_data['action']}"))
            print(_c("action",  f"   Input:   {json.dumps(step_data['action_input'], ensure_ascii=False)}"))
            print(_c("obs",     f"👁  Obs:     {step_data['observation'][:300]}"))
        elif stype == "final":
            elapsed = time.time() - start
            print(f"\n{'─'*60}")
            print(_c("final", f"\n✅ Final Answer:\n{step_data['answer']}"))
            print(f"\n共 {step_data['step']} 步，耗时 {elapsed:.1f}s")
        elif stype in ("error", "max_steps"):
            print(_c("error", f"\n⚠️  {step_data.get('answer', '')}"))

if __name__ == "__main__":
    from memory import gen_session_id
    parser = argparse.ArgumentParser()
    parser.add_argument("--question",  default="贵州茅台和五粮液2023年的毛利率哪家更高？差多少个百分点？")
    parser.add_argument("--max_steps", type=int, default=10)
    parser.add_argument("--session", type=str, help="指定会话ID，多轮对话复用上下文")
    args = parser.parse_args()
    sid = args.session if args.session else gen_session_id()
    run_and_print(args.question, sid, args.max_steps)