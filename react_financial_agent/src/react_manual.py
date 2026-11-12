"""
手写 Prompt 解析版 ReAct Agent（新增多轮会话长短记忆+解析重试+超长输出容错）
"""
import os
import re
import json
import time
import logging
import argparse
from typing import Generator, List
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

BASE_SYSTEM_PROMPT = """你是一个专业的A股金融分析助手，可以使用以下工具来回答问题：
1. rag_search(query) - 年报语义检索文本
2. company_lookup(name) - 公司名转股票代码
3. calculator(expr) - 数学计算
4. financial_indicator(symbol) - 实时财务指标
5. stock_price(symbol, start_date, end_date) - 历史股价

输出格式严格遵循：
Thought: 分析当前状态，结合历史对话上下文，决定下一步工具
Action: 工具名称
Action Input: {"参数名": "参数值"}
Observation收到后继续推理，信息充足输出：
Final Answer: 完整回答，引用数据来源

规则：
- 先用company_lookup获取代码再查财务/股价
- 所有数值计算必须使用calculator，禁止心算
- 回答需要结合本轮对话上下文与历史记忆，不要重复询问已获取信息
- 无工具可解决则直接说明原因

强制硬性约束：
1. 用户上下文明确查询2023毛利率，简写提问默认查询2023毛利率，禁止反问用户索要信息；
2. 历史存在毛利率对比需求，直接调用工具，不追问细节；
3. 任何情况下必须输出Thought+Action+Action Input三段式，禁止直接输出纯自然语言回答；
4. 工具返回数据截断缺失年份时，调用rag_search补全财务数值；
5. Action Input JSON必须完整闭合，不得残缺。
"""

# 正则解析规则
_THOUGHT_RE      = re.compile(r"Thought:\s*(.+?)(?=\nAction:|\nFinal Answer:|$)", re.DOTALL)
_ACTION_RE       = re.compile(r"Action:\s*(\w+)")
_ACTION_INPUT_RE = re.compile(r"Action Input:\s*(\{.+?\})", re.DOTALL)
_FINAL_RE        = re.compile(r"Final Answer:\s*(.+)", re.DOTALL)


def _parse_step(text: str) -> dict:
    # 拦截模型反问、闲聊类无格式输出
    if any(k in text for k in ["请问", "请提供更多细节", "哪方面", "需要进一步信息"]):
        return {"type": "unparseable", "raw": text}

    final = _FINAL_RE.search(text)
    if final:
        thought_m = _THOUGHT_RE.search(text)
        return {
            "type":    "final",
            "thought": thought_m.group(1).strip() if thought_m else "",
            "answer":  final.group(1).strip(),
        }

    thought_m = _THOUGHT_RE.search(text)
    action_m  = _ACTION_RE.search(text)
    input_m   = _ACTION_INPUT_RE.search(text)

    if not action_m:
        return {"type": "unparseable", "raw": text}

    action_input = {}
    if input_m:
        raw_json = input_m.group(1)
        left_cnt = raw_json.count("{")
        right_cnt = raw_json.count("}")
        if left_cnt > right_cnt:
            raw_json += "}" * (left_cnt - right_cnt)
        try:
            action_input = json.loads(raw_json)
        except json.JSONDecodeError:
            action_input = {}

    return {
        "type":         "action",
        "thought":      thought_m.group(1).strip() if thought_m else "",
        "action":       action_m.group(1).strip(),
        "action_input": action_input,
    }


def run(question: str, session_id: str, max_steps: int = 10) -> Generator[dict, None, None]:
    """
    带会话记忆+重试机制的ReAct循环
    :param question: 当前用户提问
    :param session_id: 会话唯一ID
    :param max_steps: 最大推理步数
    """
    from tools import TOOLS_MAP
    history_mem = recall_long_memory(question)
    full_system = BASE_SYSTEM_PROMPT
    if history_mem:
        full_system += "\n=== 历史对话记忆（参考上下文，避免重复查询）===\n" + "\n".join(history_mem) + "\n=== 结束历史记忆 ==="

    messages = get_session_messages(session_id)
    if not messages:
        messages.append({"role": "system", "content": full_system})
    user_msg = {"role": "user", "content": question}
    append_session_msg(session_id, user_msg)
    messages.append(user_msg)

    for step in range(1, max_steps + 1):
        max_retry = 2
        retry_cnt = 0
        parsed = None
        llm_output = ""

        while retry_cnt <= max_retry:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0,
                stop=["Observation:", "Observation："],
                max_tokens=1024,
            )
            finish_reason = response.choices[0].finish_reason
            llm_output = response.choices[0].message.content.strip()

            # 手动截断提前生成的Observation内容
            for flag in ("Observation:", "Observation："):
                if flag in llm_output:
                    llm_output = llm_output.split(flag)[0].strip()
                    logger.warning("模型提前输出Observation，已截断")

            if finish_reason == "length":
                logger.warning(f"Step {step} 模型输出token截断")

            parsed = _parse_step(llm_output)
            if parsed["type"] != "unparseable":
                break
            retry_cnt += 1
            logger.warning(f"Step {step} 解析失败，第{retry_cnt}次重试")

        if parsed["type"] == "unparseable":
            yield {
                "step":        step,
                "type":        "error",
                "observation": f"连续{max_retry+1}次格式解析失败，原始输出：{llm_output[:300]}",
            }
            return

        if parsed["type"] == "final":
            yield {
                "step":    step,
                "type":    "final",
                "thought": parsed["thought"],
                "answer":  parsed["answer"],
            }
            append_session_msg(session_id, {"role": "assistant", "content": llm_output})
            return

        # 执行工具
        tool_name  = parsed["action"]
        tool_args  = parsed["action_input"]
        tool_fn    = TOOLS_MAP.get(tool_name)
        if tool_fn is None:
            observation = f"未知工具 '{tool_name}'，可用工具：{list(TOOLS_MAP.keys())}"
        else:
            try:
                observation = tool_fn(**tool_args)
            except TypeError as e:
                observation = f"工具参数错误: {e}"

        step_result = {
            "step":         step,
            "type":         "action",
            "thought":      parsed["thought"],
            "action":       tool_name,
            "action_input": tool_args,
            "observation":  str(observation),
        }
        yield step_result

        assistant_msg = {"role": "assistant", "content": llm_output}
        append_session_msg(session_id, assistant_msg)
        messages.append(assistant_msg)
        obs_msg = {"role": "user", "content": f"Observation: {observation}\n"}
        append_session_msg(session_id, obs_msg)
        messages.append(obs_msg)

    yield {
        "step":   max_steps + 1,
        "type":   "max_steps",
        "answer": f"已达最大步数 {max_steps}，未能得出最终答案",
    }


# CLI彩色输出
COLORS = {
    "thought":  "\033[36m", "action":   "\033[33m", "obs":      "\033[32m",
    "final":    "\033[35m", "error":    "\033[31m", "reset":    "\033[0m",
}
def _c(color: str, text: str) -> str:
    return f"{COLORS[color]}{text}{COLORS['reset']}"

def run_and_print(question: str, session_id: str, max_steps: int = 10):
    print(f"\n{'='*60}")
    print(f"问题: {question} | 会话ID:{session_id}")
    print(f"模型: {MODEL}  实现: 手写Prompt解析（多轮记忆）")
    print('='*60)
    start = time.time()
    for step_data in run(question, session_id, max_steps=max_steps):
        stype = step_data["type"]
        if stype == "action":
            print(f"\n[Step {step_data['step']}]")
            print(_c("thought", f"🧠 Thought: {step_data['thought']}"))
            print(_c("action",  f"🔧 Action:  {step_data['action']}"))
            print(_c("action",  f"   Input:   {json.dumps(step_data['action_input'], ensure_ascii=False)}"))
            print(_c("obs",     f"👁  Obs:     {step_data['observation'][:300]}"))
        elif stype == "final":
            elapsed = time.time() - start
            print(f"\n{'─'*60}")
            if step_data.get("thought"):
                print(_c("thought", f"🧠 Thought: {step_data['thought']}"))
            print(_c("final",  f"\n✅ Final Answer:\n{step_data['answer']}"))
            print(f"\n共 {step_data['step']} 步，耗时 {elapsed:.1f}s")
        elif stype in ("error", "max_steps"):
            print(_c("error", f"\n⚠️  {step_data.get('answer', step_data.get('observation', ''))}"))

if __name__ == "__main__":
    from memory import gen_session_id
    parser = argparse.ArgumentParser()
    parser.add_argument("--question",  default="贵州茅台和五粮液2023年的毛利率哪家更高？差多少个百分点？")
    parser.add_argument("--max_steps", type=int, default=10)
    parser.add_argument("--session", type=str, help="指定会话ID，多轮对话复用上下文")
    args = parser.parse_args()
    sid = args.session if args.session else gen_session_id()
    run_and_print(args.question, sid, args.max_steps)