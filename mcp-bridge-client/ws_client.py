"""WebSocket客户端模块 - 连接远程bridge-server"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Callable, Optional

import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


class BridgeWSClient:
    """WebSocket客户端，连接远程bridge-server"""
    
    def __init__(
        self,
        server_url: str,
        client_id: str,
        on_call: Callable[[str, str, Dict[str, Any]], Any]
    ):
        self.server_url = server_url
        self.client_id = client_id
        self.on_call = on_call  # 工具调用回调
        self._ws: Optional[WebSocketClientProtocol] = None
        self._running = False
    
    async def connect(self) -> None:
        """连接到bridge-server"""
        logger.info(f"连接到 bridge-server: {self.server_url}")
        self._ws = await websockets.connect(self.server_url)
        self._running = True
        logger.info("WebSocket连接成功")
    
    async def register_tools(self, tools: List[Dict[str, Any]]) -> None:
        """向bridge-server注册工具列表"""
        if not self._ws:
            raise RuntimeError("WebSocket未连接")
        
        message = {
            "type": "register",
            "client_id": self.client_id,
            "tools": tools
        }
        await self._ws.send(json.dumps(message))
        logger.info(f"已注册 {len(tools)} 个工具到 bridge-server")
    
    async def send_result(self, request_id: str, result: Any, error: str = None) -> None:
        """发送工具调用结果"""
        if not self._ws:
            return
        
        message = {
            "type": "result",
            "request_id": request_id,
            "result": result,
            "error": error
        }
        await self._ws.send(json.dumps(message))
    
    async def listen(self) -> None:
        """监听来自bridge-server的消息"""
        if not self._ws:
            raise RuntimeError("WebSocket未连接")
        
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误: {e}")
        except websockets.ConnectionClosed:
            logger.info("WebSocket连接已关闭")
            self._running = False
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """处理收到的消息"""
        msg_type = data.get("type")
        
        if msg_type == "call":
            # 工具调用请求
            request_id = data.get("request_id")
            server = data.get("server")
            method = data.get("method")
            args = data.get("args", {})
            
            logger.info(f"收到工具调用请求: {server}/{method}")
            
            try:
                result = await self.on_call(server, method, args)
                # 序列化MCP结果
                if hasattr(result, "content"):
                    # MCP CallToolResult
                    result_data = [
                        {"type": c.type, "text": getattr(c, "text", None)}
                        for c in result.content
                    ]
                else:
                    result_data = result
                await self.send_result(request_id, result_data)
            except Exception as e:
                logger.error(f"工具调用失败: {e}")
                await self.send_result(request_id, None, str(e))
        
        elif msg_type == "ping":
            # 心跳响应
            await self._ws.send(json.dumps({"type": "pong"}))
        
        else:
            logger.warning(f"未知消息类型: {msg_type}")
    
    async def close(self) -> None:
        """关闭连接"""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
