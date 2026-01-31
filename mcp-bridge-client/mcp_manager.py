"""MCP Server进程管理模块"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from config import ServerConfig

logger = logging.getLogger(__name__)


class MCPServerManager:
    """管理多个本地MCP Server进程"""
    
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.tools: Dict[str, Dict[str, Any]] = {}  # server_name -> {tool_name: tool_schema}
        self._exit_stack: Optional[AsyncExitStack] = None
    
    async def start_server(self, config: ServerConfig) -> None:
        """启动单个MCP Server"""
        logger.info(f"启动MCP Server: {config.name}")
        
        server_params = StdioServerParameters(
            command=config.command,
            args=config.args
        )
        
        # 使用stdio_client连接MCP Server
        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = stdio_transport
        
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        
        # 初始化会话
        await session.initialize()
        
        # 获取工具列表
        tools_response = await session.list_tools()
        
        self.sessions[config.name] = session
        self.tools[config.name] = {
            tool.name: {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            }
            for tool in tools_response.tools
        }
        
        logger.info(f"MCP Server {config.name} 启动成功，工具数: {len(self.tools[config.name])}")
    
    async def start_all(self, configs: List[ServerConfig]) -> None:
        """启动所有配置的MCP Server"""
        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()
        
        for config in configs:
            try:
                await self.start_server(config)
            except Exception as e:
                logger.error(f"启动MCP Server {config.name} 失败: {e}")
    
    async def stop_all(self) -> None:
        """停止所有MCP Server"""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
        self.sessions.clear()
        self.tools.clear()
        logger.info("所有MCP Server已停止")
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """获取所有已注册的工具列表（带server前缀）"""
        all_tools = []
        for server_name, tools in self.tools.items():
            for tool_name, tool_schema in tools.items():
                # 添加server前缀，格式: server__tool
                prefixed_name = f"{server_name}__{tool_name}"
                all_tools.append({
                    "name": prefixed_name,
                    "description": tool_schema.get("description", ""),
                    "inputSchema": tool_schema.get("inputSchema", {}),
                    "_server": server_name,
                    "_original_name": tool_name
                })
        return all_tools
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用指定server的工具"""
        if server_name not in self.sessions:
            raise ValueError(f"未知的MCP Server: {server_name}")
        
        session = self.sessions[server_name]
        result = await session.call_tool(tool_name, arguments)
        return result
