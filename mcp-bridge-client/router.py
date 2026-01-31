"""请求路由模块 - 将远程调用路由到正确的本地MCP Server"""
import logging
from typing import Dict, Any

from mcp_manager import MCPServerManager

logger = logging.getLogger(__name__)


class RequestRouter:
    """请求路由器"""
    
    def __init__(self, mcp_manager: MCPServerManager):
        self.mcp_manager = mcp_manager
    
    async def route_call(self, server: str, method: str, args: Dict[str, Any]) -> Any:
        """路由工具调用到对应的MCP Server"""
        logger.debug(f"路由调用: {server}/{method}")
        
        if server not in self.mcp_manager.sessions:
            raise ValueError(f"未知的MCP Server: {server}")
        
        result = await self.mcp_manager.call_tool(server, method, args)
        return result
