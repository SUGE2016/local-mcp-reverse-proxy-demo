"""MCP Bridge Server 入口"""
import logging
from typing import Dict, Any

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ws_handler import handle_websocket
from mcp_server import list_tools, call_tool

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title="MCP Bridge Server")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ToolCallRequest(BaseModel):
    """工具调用请求"""
    name: str
    arguments: Dict[str, Any] = {}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点 - 接收bridge-client连接"""
    await handle_websocket(websocket)


@app.get("/tools")
async def get_tools():
    """获取所有已注册的工具列表"""
    tools = await list_tools()
    return {"tools": tools}


@app.post("/tools/call")
async def call_tool_endpoint(request: ToolCallRequest):
    """调用工具"""
    result = await call_tool(request.name, request.arguments)
    return result


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


@app.get("/clients")
async def get_clients():
    """获取已连接的客户端列表"""
    from registry import registry
    return {
        "clients": [
            {
                "client_id": client_id,
                "tool_count": len(conn.tools)
            }
            for client_id, conn in registry.clients.items()
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
