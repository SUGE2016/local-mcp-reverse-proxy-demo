"""工具注册表模块 - 存储已注册的工具和客户端连接"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class ClientConnection:
    """客户端连接信息"""
    client_id: str
    websocket: WebSocket
    tools: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    pending_requests: Dict[str, asyncio.Future] = field(default_factory=dict)


class Registry:
    """工具注册表"""
    
    def __init__(self):
        self.clients: Dict[str, ClientConnection] = {}  # client_id -> ClientConnection
        self.tool_to_client: Dict[str, str] = {}  # tool_name -> client_id
    
    def register_client(self, client_id: str, websocket: WebSocket) -> ClientConnection:
        """注册新客户端"""
        conn = ClientConnection(client_id=client_id, websocket=websocket)
        self.clients[client_id] = conn
        logger.info(f"客户端已连接: {client_id}")
        return conn
    
    def unregister_client(self, client_id: str) -> None:
        """注销客户端"""
        if client_id in self.clients:
            conn = self.clients[client_id]
            # 移除该客户端的所有工具
            for tool_name in conn.tools.keys():
                if tool_name in self.tool_to_client:
                    del self.tool_to_client[tool_name]
            # 取消所有pending请求
            for future in conn.pending_requests.values():
                if not future.done():
                    future.set_exception(Exception("客户端断开连接"))
            del self.clients[client_id]
            logger.info(f"客户端已断开: {client_id}")
    
    def register_tools(self, client_id: str, tools: List[Dict[str, Any]]) -> None:
        """注册客户端的工具"""
        if client_id not in self.clients:
            raise ValueError(f"未知的客户端: {client_id}")
        
        conn = self.clients[client_id]
        for tool in tools:
            tool_name = tool["name"]
            conn.tools[tool_name] = tool
            self.tool_to_client[tool_name] = client_id
        
        logger.info(f"客户端 {client_id} 注册了 {len(tools)} 个工具")
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """获取所有已注册的工具"""
        all_tools = []
        for conn in self.clients.values():
            all_tools.extend(conn.tools.values())
        return all_tools
    
    def get_client_for_tool(self, tool_name: str) -> Optional[ClientConnection]:
        """根据工具名获取对应的客户端连接"""
        client_id = self.tool_to_client.get(tool_name)
        if client_id:
            return self.clients.get(client_id)
        return None
    
    def parse_tool_name(self, tool_name: str) -> tuple:
        """解析工具名，提取server和method
        格式: server__method
        """
        if "__" in tool_name:
            parts = tool_name.split("__", 1)
            return parts[0], parts[1]
        return None, tool_name


# 全局注册表实例
registry = Registry()
