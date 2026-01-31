"""Web Agent 入口"""
import os
import json
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import AsyncOpenAI

from mcp_client import MCPClient
from agent import Agent

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = os.getenv("OPENAI_API_URL")  # 支持自定义API URL
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
BRIDGE_SERVER_URL = os.getenv("BRIDGE_SERVER_URL", "http://localhost:8001")

# 创建FastAPI应用
app = FastAPI(title="Web Agent")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化客户端
openai_client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_URL  # 支持自定义base_url
) if OPENAI_API_KEY else None
mcp_client = MCPClient(BRIDGE_SERVER_URL)


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str


@app.post("/chat")
async def chat(request: ChatRequest):
    """聊天接口 - 返回SSE流"""
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI API key未配置")
    
    agent = Agent(openai_client, mcp_client, model=OPENAI_MODEL)
    
    async def generate():
        async for event in agent.chat(request.message):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@app.post("/chat/sync")
async def chat_sync(request: ChatRequest):
    """同步聊天接口 - 返回完整响应"""
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI API key未配置")
    
    agent = Agent(openai_client, mcp_client, model=OPENAI_MODEL)
    
    events = []
    final_message = ""
    
    async for event in agent.chat(request.message):
        events.append(event)
        if event["type"] == "message":
            final_message = event["content"]
    
    return {
        "message": final_message,
        "events": events
    }


@app.get("/tools")
async def get_tools():
    """获取可用工具列表"""
    tools = await mcp_client.list_tools()
    return {"tools": tools}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
