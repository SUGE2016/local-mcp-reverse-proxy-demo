"""MCP Client模块 - 连接bridge-server获取和调用工具"""
import logging
from typing import Dict, Any, List

import httpx

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP Client - 通过HTTP与bridge-server通信"""
    
    def __init__(self, bridge_server_url: str):
        self.bridge_server_url = bridge_server_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=60.0)
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具"""
        try:
            response = await self._client.get(f"{self.bridge_server_url}/tools")
            response.raise_for_status()
            data = response.json()
            return data.get("tools", [])
        except Exception as e:
            logger.error(f"获取工具列表失败: {e}")
            return []
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        try:
            response = await self._client.post(
                f"{self.bridge_server_url}/tools/call",
                json={"name": name, "arguments": arguments}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"调用工具失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()
    
    def tools_to_openai_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将MCP工具转换为OpenAI function calling格式"""
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {"type": "object", "properties": {}})
                }
            })
        return openai_tools
