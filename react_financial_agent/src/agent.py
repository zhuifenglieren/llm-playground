"""
统一入口：切换手写版 / Function Calling 版 ReAct Agent，支持多轮会话记忆

使用方式（单轮自动生成session）：
  python agent.py --mode manual --question "茅台2023毛利率"
多轮对话（复用同一个session_id保留上下文）：
  python agent.py --session s123 --mode manual --question "茅台营收"
  python agent.py --session s123 --mode manual --question "对比五粮液"
"""
import os
import argparse
from memory import gen_session_id

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
DEFAULT_QUESTION = "贵州茅台和五粮液2023年的毛利率哪家更高？差多少个百分点？"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ReAct Financial Agent 多轮会话版")
    parser.add_argument(
        "--mode", choices=["manual", "fc"], default="manual",
        help="manual=手写Prompt解析版  fc=Function Calling版",
    )
    parser.add_argument("--question",  default=DEFAULT_QUESTION)
    parser.add_argument("--max_steps", type=int, default=10)
    parser.add_argument("--session", type=str, help="自定义会话ID，多轮对话复用上下文，不填自动生成")
    args = parser.parse_args()

    # 生成/读取会话ID
    session_id = args.session if args.session else gen_session_id()
    print(f"当前会话ID：{session_id}，如需多轮对话请带上--session参数")

    if args.mode == "manual":
        from react_manual import run_and_print
    else:
        from react_function_calling import run_and_print

    run_and_print(args.question, session_id, args.max_steps)