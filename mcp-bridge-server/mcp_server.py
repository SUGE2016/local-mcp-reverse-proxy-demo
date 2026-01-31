"""MCP Server接口模块 - 对外暴露标准MCP接口"""
import logging
from typing import Dict, Any, List

from registry import registry
from ws_handler import call_tool_on_client

logger = logging.getLogger(__name__)


async def list_tools() -> List[Dict[str, Any]]:
    """获取所有已注册的工具列表"""
    tools = registry.get_all_tools()
    # 返回标准MCP格式
    return [
        {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "inputSchema": tool.get("inputSchema", {})
        }
        for tool in tools
    ]


async def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """调用工具"""
    logger.info(f"调用工具: {name}")
    
    try:
        result = await call_tool_on_client(name, arguments)
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.error(f"工具调用失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }
