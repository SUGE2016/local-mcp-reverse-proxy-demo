"""WebSocket处理模块 - 处理客户端连接和消息"""
import asyncio
import json
import logging
import uuid
from typing import Dict, Any

from fastapi import WebSocket, WebSocketDisconnect

from registry import registry, ClientConnection

logger = logging.getLogger(__name__)


async def handle_websocket(websocket: WebSocket) -> None:
    """处理WebSocket连接"""
    await websocket.accept()
    
    client_id = None
    conn = None
    
    try:
        async for message in websocket.iter_text():
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "register":
                    # 客户端注册
                    client_id = data.get("client_id", str(uuid.uuid4()))
                    tools = data.get("tools", [])
                    
                    conn = registry.register_client(client_id, websocket)
                    registry.register_tools(client_id, tools)
                    
                    # 发送确认
                    await websocket.send_json({
                        "type": "registered",
                        "client_id": client_id,
                        "tool_count": len(tools)
                    })
                
                elif msg_type == "result":
                    # 工具调用结果
                    request_id = data.get("request_id")
                    result = data.get("result")
                    error = data.get("error")
                    
                    if conn and request_id in conn.pending_requests:
                        future = conn.pending_requests.pop(request_id)
                        if error:
                            future.set_exception(Exception(error))
                        else:
                            future.set_result(result)
                
                elif msg_type == "pong":
                    # 心跳响应
                    pass
                
                else:
                    logger.warning(f"未知消息类型: {msg_type}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误: {e}")
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket断开: {client_id}")
    finally:
        if client_id:
            registry.unregister_client(client_id)


async def call_tool_on_client(tool_name: str, arguments: Dict[str, Any], timeout: float = 30.0) -> Any:
    """通过WebSocket调用客户端的工具"""
    conn = registry.get_client_for_tool(tool_name)
    if not conn:
        raise ValueError(f"未找到工具 {tool_name} 对应的客户端")
    
    # 解析工具名
    server, method = registry.parse_tool_name(tool_name)
    
    # 生成请求ID
    request_id = str(uuid.uuid4())
    
    # 创建Future等待结果
    future = asyncio.get_event_loop().create_future()
    conn.pending_requests[request_id] = future
    
    # 发送调用请求
    await conn.websocket.send_json({
        "type": "call",
        "request_id": request_id,
        "server": server,
        "method": method,
        "args": arguments
    })
    
    # 等待结果
    try:
        result = await asyncio.wait_for(future, timeout=timeout)
        return result
    except asyncio.TimeoutError:
        conn.pending_requests.pop(request_id, None)
        raise TimeoutError(f"工具调用超时: {tool_name}")
