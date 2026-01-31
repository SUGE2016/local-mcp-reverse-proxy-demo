"""MCP Bridge Client 入口"""
import asyncio
import logging
import sys
from pathlib import Path

from config import load_config
from mcp_manager import MCPServerManager
from ws_client import BridgeWSClient
from router import RequestRouter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """主函数"""
    # 加载配置
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    logger.info(f"加载配置: {config_path}")
    config = load_config(config_path)
    
    # 创建sandbox目录（如果需要）
    sandbox_path = Path("./sandbox")
    if not sandbox_path.exists():
        sandbox_path.mkdir(parents=True)
        logger.info(f"创建sandbox目录: {sandbox_path.absolute()}")
    
    # 初始化MCP Server管理器
    mcp_manager = MCPServerManager()
    router = RequestRouter(mcp_manager)
    
    # 启动所有本地MCP Server
    logger.info("启动本地MCP Server...")
    await mcp_manager.start_all(config.servers)
    
    # 获取所有工具列表
    tools = mcp_manager.get_all_tools()
    logger.info(f"共发现 {len(tools)} 个工具")
    for tool in tools:
        logger.info(f"  - {tool['name']}: {tool.get('description', '')[:50]}")
    
    # 创建WebSocket客户端
    ws_client = BridgeWSClient(
        server_url=config.bridge_server_url,
        client_id=config.client_id,
        on_call=router.route_call
    )
    
    # 连接到bridge-server
    try:
        await ws_client.connect()
        
        # 注册工具
        await ws_client.register_tools(tools)
        
        # 监听消息
        logger.info("开始监听远程调用...")
        await ws_client.listen()
        
    except Exception as e:
        logger.error(f"连接错误: {e}")
    finally:
        # 清理
        await ws_client.close()
        await mcp_manager.stop_all()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("收到中断信号，退出...")
