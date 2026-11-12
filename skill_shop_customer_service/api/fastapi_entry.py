import os
import sys
import time
import uuid
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import requests

BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

app = FastAPI(title="电商智能客服‑FAQ自动进化版")

# 跨域优先加载
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态资源挂载
static_path = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")
FAQ_PATH = static_path / "faq_config.md"
SAMPLE_STORE_PATH = static_path / "chat_sample.json"

# 首页路由
@app.get("/")
async def root():
    return FileResponse(static_path / "index.html")


class ChatRequest(BaseModel):
    session_id: str = None
    user_openid: str
    user_query: str
    order_no: str = None


# ---------------------- 全局配置 ----------------------
MODULE_TTL = 120
_module_cache = {}
# DashScope 密钥，环境变量传入
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
EVOLVE_TRIGGER_SAMPLES = 10  # 收集10条对话触发自动进化


def dynamic_import(mod_name: str):
    now = time.time()
    if mod_name in _module_cache:
        obj, stamp = _module_cache[mod_name]
        if now - stamp < MODULE_TTL:
            return obj
    mod = __import__(mod_name)
    _module_cache[mod_name] = (mod, now)
    return mod


# ---------------------- FAQ读取、解析、意图匹配 ----------------------
def load_raw_faq() -> str:
    if FAQ_PATH.exists():
        return FAQ_PATH.read_text(encoding="utf-8")
    return ""


def parse_faq_intents():
    """解析md，返回 {intent_tag:question_list}"""
    raw = load_raw_faq()
    lines = [i.strip() for i in raw.splitlines() if i.strip()]
    intent_map = dict()
    current_tag = "unknown"
    for line in lines:
        if line.startswith("##"):
            current_tag = line
            intent_map[current_tag] = []
        elif line[0].isdigit():
            # 剥离序号
            q = "".join(line.split(".")[1:]).strip()
            intent_map[current_tag].append(q)
    return intent_map


def intent_match(user_text: str):
    """简单关键词命中返回意图分类名称"""
    intent_dict = parse_faq_intents()
    user_text = user_text.lower()
    for tag, qs in intent_dict.items():
        for question in qs:
            if any(word in user_text for word in question.lower().split()):
                return tag
    return "未匹配‑未知咨询意图"


# ---------------------- Qwen‑max 请求封装 自动生成回答 ----------------------
def qwen_max_reply(user_query: str, intent_name: str, faq_data: str):
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""
你现在是电商平台客服，根据下面常见知识库回答用户问题，回答简短友好。
【FAQ知识库】
{faq_data}
【识别到用户意图】{intent_name}
【用户问题】{user_query}
只输出客服回复，不要多余解释。
"""
    payload = {
        "model": "qwen-max",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    res_json = resp.json()
    answer = res_json["choices"][0]["message"]["content"].strip()
    return answer


# ---------------------- 对话样本持久化 & 自动进化逻辑 ----------------------
def load_chat_samples():
    if SAMPLE_STORE_PATH.exists():
        text = SAMPLE_STORE_PATH.read_text(encoding="utf-8")
        return json.loads(text)
    return []


def save_chat_samples(sample_list):
    with open(SAMPLE_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(sample_list, f, ensure_ascii=False, indent=2)


def faq_auto_evolve(samples):
    """基于用户真实咨询样本，调用大模型更新faq_config.md，扩充常见问题"""
    faq_text = load_raw_faq()
    prompt = f"""
下面是现有的电商客服FAQ文档：
{faq_text}
下面是最近收集到的用户咨询对话样本：
{json.dumps(samples,ensure_ascii=False)}
请分析用户新问题，将没有收录进FAQ的全新问题补充进去，保持原有markdown结构，只输出完整新版md文本。
"""
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "qwen-max",
        "messages": [{"role": "user", "content": prompt}],
        "temperature":0.3
    }
    res = requests.post(url,headers=headers,json=payload,timeout=40)
    new_md = res.json()["choices"][0]["message"]["content"].strip()
    # 写入更新FAQ配置
    FAQ_PATH.write_text(new_md,encoding="utf-8")
    # 清空本轮样本
    return []


# ---------------------- 聊天主接口 ----------------------
@app.post("/skill/shop_service/chat")
async def chat(req: ChatRequest):
    t_start = time.perf_counter()
    sid = req.session_id if req.session_id else str(uuid.uuid4())
    user_query = req.user_query.strip()

    # 1.意图识别
    hit_intent = intent_match(user_query)
    faq_source = load_raw_faq()

    # 2.调用Qwen‑Max生成应答
    reply = qwen_max_reply(user_query,hit_intent,faq_source)

    # 3.保存对话样本
    samples = load_chat_samples()
    one_sample = {
        "session_id": sid,
        "openid": req.user_openid,
        "query": user_query,
        "intent": hit_intent,
        "response": reply,
        "cost_ms": int((time.perf_counter()-t_start)*1000)
    }
    samples.append(one_sample)

    # 4.达到样本阈值，触发FAQ自动进化更新
    if len(samples) >= EVOLVE_TRIGGER_SAMPLES:
        samples = faq_auto_evolve(samples)

    save_chat_samples(samples)

    return {
        "session_id": sid,
        "response": reply,
        "current_intent": hit_intent,
        "state": "wait_user_question",
        "sentiment": "neutral",
        "pending_tasks": []
    }