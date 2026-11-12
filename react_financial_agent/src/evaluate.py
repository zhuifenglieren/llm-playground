import os
import json
import time
import argparse
import logging
import sys

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
sys.path.insert(0, os.path.dirname(__file__))

# 提升日志可见
logging.basicConfig(level=logging.INFO)

EVAL_QUESTIONS = [
    {
        "id": "Q1",
        "question": "贵州茅台和五粮液2023年的毛利率哪家更高？差多少个百分点？",
        "expected_tools": ["rag_search", "rag_search", "calculator"],
        "note": "跨公司对比 + 计算",
    },
    {
        "id": "Q2",
        "question": "宁德时代2021年到2023年的营业收入分别是多少？复合增长率是多少？",
        "expected_tools": ["rag_search", "rag_search", "calculator"],
        "note": "跨年度趋势 + CAGR计算",
    },
    {
        "id": "Q3",
        "question": "海康威视2023年年报中提到了哪些主要风险因素？",
        "expected_tools": ["rag_search"],
        "note": "单次检索，定性问题",
    },
    {
        "id": "Q4",
        "question": "贵州茅台过去一年（2023年全年）的股价涨跌幅是多少？",
        "expected_tools": ["company_lookup", "stock_price", "calculator"],
        "note": "股价查询 + 计算",
    },
    {
        "id": "Q5",
        "question": "请预测明年A股市场的走势",
        "expected_tools": [],
        "note": "超出能力边界，应拒绝作答",
    },
]


def _run_single(mode: str, question: str, max_steps: int = 10) -> dict:
    from memory import gen_session_id, clear_session
    eval_sid = gen_session_id()
    print(f"    开始执行 {mode} 会话 {eval_sid}", flush=True)
    try:
        if mode == "manual":
            from react_manual import run as react_run
        else:
            from react_function_calling import run as react_run

        steps = []
        parse_errors = 0
        start = time.time()
        final_answer = None
        success = False

        for step_data in react_run(question, eval_sid, max_steps=max_steps):
            print(f"      推理步骤: {step_data['type']}", flush=True)
            steps.append(step_data)
            if step_data["type"] == "unparseable":
                parse_errors += 1
            if step_data["type"] == "final":
                final_answer = step_data["answer"]
                success = True

        elapsed = time.time() - start
        action_steps = [s for s in steps if s["type"] == "action"]
        tools_used = [s["action"] for s in action_steps]
        clear_session(eval_sid)
        return {
            "mode": mode,
            "total_steps": len(action_steps),
            "elapsed_s": round(elapsed, 1),
            "success": success,
            "parse_errors": parse_errors,
            "tools_used": tools_used,
            "final_answer": (final_answer or "")[:200],
        }
    except Exception as e:
        clear_session(eval_sid)
        print(f"    [{mode}] 执行异常: {repr(e)}", flush=True)
        return {
            "mode": mode,
            "total_steps": 0,
            "elapsed_s": 0,
            "success": False,
            "parse_errors": 0,
            "tools_used": [],
            "final_answer": f"执行失败:{repr(e)}",
        }


def evaluate(output_path: str | None = None, max_steps: int = 10):
    results = []
    print("===== 开始批量评估 =====", flush=True)
    for q in EVAL_QUESTIONS:
        print(f"\n{'─'*60}", flush=True)
        print(f"[{q['id']}] {q['question']}", flush=True)
        print(f"  预期工具: {q['expected_tools']}  ({q['note']})", flush=True)
        for mode in ["manual", "fc"]:
            print(f"  运行 [{mode}]...", end=" ", flush=True)
            r = _run_single(mode, q["question"], max_steps)
            print(f"步骤:{r['total_steps']}  耗时:{r['elapsed_s']}s  成功:{r['success']}", flush=True)
            results.append({**q, **r})

    print(f"\n{'='*60}", flush=True)
    print(f"{'ID':<4} {'Mode':<8} {'Steps':<7} {'Time(s)':<9} {'Success':<8} {'ParseErr'}", flush=True)
    print(f"{'─'*60}", flush=True)
    for r in results:
        print(
            f"{r['id']:<4} {r['mode']:<8} {r['total_steps']:<7} "
            f"{r['elapsed_s']:<9} {str(r['success']):<8} {r['parse_errors']}",
            flush=True
        )
    # 汇总
    for mode in ["manual", "fc"]:
        mode_results = [r for r in results if r["mode"] == mode]
        avg_steps = sum(r["total_steps"] for r in mode_results) / len(mode_results)
        avg_time = sum(r["elapsed_s"] for r in mode_results) / len(mode_results)
        success_rate = sum(r["success"] for r in mode_results) / len(mode_results)
        total_errors = sum(r["parse_errors"] for r in mode_results)
        print(f"\n[{mode}] 平均步数:{avg_steps:.1f}  平均耗时:{avg_time:.1f} 成功率:{success_rate:.0%} 解析错误:{total_errors}", flush=True)
    if output_path:
        def _safe(v):
            return v.item() if hasattr(v, "item") else v
        safe_results = [{k: _safe(v) for k, v in r.items()} for r in results]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(safe_results, f, ensure_ascii=False, indent=2)
        print(f"\n评估结果已保存至: {output_path}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=None, help="保存JSON路径")
    parser.add_argument("--max_steps", type=int, default=10)
    args = parser.parse_args()
    try:
        evaluate(args.output, args.max_steps)
    except Exception as e:
        print(f"顶层评估异常：{repr(e)}", flush=True)