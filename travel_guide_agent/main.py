"""
旅游指南Agent主程序
FastAPI后端服务
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from src.main_agent import TravelGuideMainAgent

# 加载环境变量
load_dotenv()

# 创建FastAPI应用
app = FastAPI(title="旅游指南Agent", description="基于Qwen-max的旅游指南智能助手")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建主Agent实例
main_agent = TravelGuideMainAgent()


# 定义请求模型
class QueryRequest(BaseModel):
    query: str
    origin: Optional[str] = None
    destination: Optional[str] = None


# 定义响应模型
class QueryResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@app.get("/")
async def read_root():
    """返回前端页面"""
    return FileResponse("static/index.html")


@app.post("/api/query")
async def process_query(request: QueryRequest):
    """处理用户查询"""
    try:
        # 如果提供了明确的出发地和目的地，直接使用
        if request.origin and request.destination:
            query = f"从{request.origin}去{request.destination}旅游"
        else:
            query = request.query

        # 处理查询
        result = await main_agent.process_query(query)

        if "error" in result:
            return QueryResponse(success=False, error=result["error"])

        return QueryResponse(success=True, data=result)

    except Exception as e:
        return QueryResponse(success=False, error=str(e))


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "message": "旅游指南Agent运行正常"}


# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    # 检查环境变量
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("警告: 未设置DASHSCOPE_API_KEY环境变量")
        print("将使用默认数据兜底")
        print("建议: 在.env文件中设置DASHSCOPE_API_KEY")

    # 启动服务
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )