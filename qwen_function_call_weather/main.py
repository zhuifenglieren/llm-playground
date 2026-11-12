import json
from llm.qwen_client import QwenLocalClient
from tools.tool_register import parse_tool_call, execute_tool
from config.settings import SYSTEM_PROMPT

def main():
    print("=============================================")
    print("    Qwen本地Function Call天气助手启动程序    ")
    print("  支持：城市查坐标 / 城市查天气 / 坐标查天气  ")
    print("  输入 exit 可退出程序                        ")
    print("=============================================\n")

    # 加载本地Qwen模型
    llm = QwenLocalClient()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("[Main] 初始化对话上下文，加载系统提示词完成")

    while True:
        user_input = input("用户：")
        if user_input.strip().lower() == "exit":
            print("[Main] 收到退出指令，程序结束")
            break
        if not user_input.strip():
            print("[Main] 输入为空，请重新提问")
            continue

        print(f"[Main] 新增用户对话消息：{user_input}")
        messages.append({"role": "user", "content": user_input})

        # LLM推理
        resp = llm.chat(messages)
        print(f"\n[Main] LLM原始输出内容：\n{resp}\n")

        # 解析是否需要调用工具
        tool_call = parse_tool_call(resp)
        if tool_call:
            # 执行工具
            tool_result = execute_tool(tool_call)
            print(f"\n[Main] 工具完整返回结果：\n{tool_result}\n")

            # 将工具结果加入对话，让模型整合回答
            print("[Main] 将工具返回结果作为tool消息送入模型二次生成总结")
            messages.append({"role": "tool", "content": tool_result})
            final_ans = llm.chat(messages)
            print(f"\n助手最终整合回答：{final_ans}\n")
            messages.append({"role": "assistant", "content": final_ans})
        else:
            # 无需工具，直接输出回答
            print(f"\n助手：{resp}\n")
            messages.append({"role": "assistant", "content": resp})

if __name__ == "__main__":
    main()