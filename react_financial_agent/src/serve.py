import os
import sys
import json
import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 必须先实例化 app，再写路由
app = FastAPI(title="ReAct Financial Agent")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
@app.get("/")
async def root():
    # __file__ = src/serve.py
    # parent.parent = 项目根目录
    html_path = Path(__file__).parent.parent / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>文件缺失</h2><p>index.html 需要放在项目根目录，和src文件夹同级</p>")

# ── 预加载 FAISS（启动时执行一次）────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("预加载 FAISS 索引和 Embedding 模型...")
    from tools import _load_rag
    await asyncio.to_thread(_load_rag)
    logger.info("预加载完成，服务就绪")
    yield

app.router.lifespan_context = lifespan

# ── 请求/响应模型 ─────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    question:  str
    max_steps: int = 10
    session_id: str = None

# 流式函数增加session_id
async def _stream_react(question: str, max_steps: int, mode: str, session_id: str):
    if mode == "manual":
        from react_manual import run as react_run
    else:
        from react_function_calling import run as react_run
    queue: asyncio.Queue = asyncio.Queue()
    _SENTINEL = object()
    def _worker():
        try:
            for step_data in react_run(question, session_id, max_steps=max_steps):
                queue.put_nowait(step_data)
        finally:
            queue.put_nowait(_SENTINEL)
    yield _sse({"type": "start", "question": question, "mode": mode, "session_id": session_id})
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _worker)
    while True:
        step_data = await queue.get()
        if step_data is _SENTINEL:
            break
        yield _sse(step_data)
    yield _sse({"type": "done"})

# 路由改造
@app.post("/query/manual")
async def query_manual(req: QueryRequest):
    from react_manual import run
    def generator():
        for item in run(req.question, req.session_id, req.max_steps):
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
    return StreamingResponse(generator(), media_type="text/event-stream")

@app.post("/query/fc")
async def query_fc(req: QueryRequest):
    from react_function_calling import run
    def generator():
        for item in run(req.question, req.session_id, req.max_steps):
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type':'done'}, ensure_ascii=False)}\n\n"
    return StreamingResponse(generator(), media_type="text/event-stream")