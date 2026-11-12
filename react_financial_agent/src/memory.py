"""
长短记忆管理器：
短期记忆：Session级完整对话上下文，多轮问答复用
长期记忆：全局摘要记忆池，存储历史问答关键结论，新query自动召回
"""
import json
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# 全局会话存储：session_id -> 对话消息列表
SESSION_STORE: Dict[str, List[dict]] = {}
# 长期记忆池：存储历史问答摘要、财务结论、工具检索结果
LONG_TERM_MEMORY: List[dict] = []
# 最大单会话消息条数（超限自动压缩摘要存入长期记忆）
MAX_SHORT_MEMORY_MSG = 8
# 长期记忆召回条数
RECALL_MEM_NUM = 3

@dataclass
class MemoryItem:
    """长期记忆条目"""
    query: str               # 用户历史问题
    summary: str             # 对话摘要（关键财务数据、结论）
    create_time: str         # 创建时间
    company_list: List[str]  # 涉及公司，用于匹配召回

def gen_session_id() -> str:
    """生成唯一会话ID"""
    return hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:16]

def get_session_messages(session_id: str) -> List[dict]:
    """获取会话短期上下文，不存在则初始化"""
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = []
    return SESSION_STORE[session_id]

def append_session_msg(session_id: str, msg: dict):
    """追加消息到短期会话记忆，超限自动压缩存入长期记忆"""
    msg_list = get_session_messages(session_id)
    msg_list.append(msg)
    # 消息超限，压缩摘要
    if len(msg_list) > MAX_SHORT_MEMORY_MSG:
        compress_session_to_long_memory(session_id, msg_list)
        # 保留最后4条最新消息作为短期上下文
        SESSION_STORE[session_id] = msg_list[-4:]

def compress_session_to_long_memory(session_id: str, msg_list: List[dict]):
    """压缩当前会话历史，生成摘要存入长期记忆"""
    user_queries = []
    final_answers = []
    company_mention = set()
    for m in msg_list:
        if m["role"] == "user":
            user_queries.append(m["content"])
            # 提取公司名
            for comp in ["贵州茅台", "五粮液", "宁德时代", "中国平安", "海康威视"]:
                if comp in m["content"]:
                    company_mention.add(comp)
        if m["role"] == "assistant" and "Final Answer:" in m["content"]:
            final_answers.append(m["content"])
    # 拼接摘要
    summary = f"历史问题：{user_queries[-1]}；核心结论：{final_answers[-1] if final_answers else '无'}"
    memory = MemoryItem(
        query=user_queries[-1],
        summary=summary,
        create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        company_list=list(company_mention)
    )
    LONG_TERM_MEMORY.append(asdict(memory))

def recall_long_memory(query: str) -> List[str]:
    """根据当前query召回相关长期记忆摘要，拼入System Prompt"""
    match_comp = []
    for comp in ["贵州茅台", "五粮液", "宁德时代", "中国平安", "海康威视"]:
        if comp in query:
            match_comp.append(comp)
    # 匹配相同公司的历史记忆
    recall = []
    for mem in LONG_TERM_MEMORY[-20:]:
        if any(c in mem["company_list"] for c in match_comp):
            recall.append(f"【历史对话记忆】{mem['summary']}")
    return recall[:RECALL_MEM_NUM]

def clear_session(session_id: str):
    """清空单会话短期记忆"""
    if session_id in SESSION_STORE:
        del SESSION_STORE[session_id]

def clear_all_memory():
    """清空所有短期+长期记忆"""
    SESSION_STORE.clear()
    LONG_TERM_MEMORY.clear()