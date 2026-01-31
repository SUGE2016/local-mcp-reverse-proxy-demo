"""配置加载模块"""
import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List


@dataclass
class ServerConfig:
    """单个MCP Server配置"""
    name: str
    command: str
    args: List[str]


@dataclass
class Config:
    """全局配置"""
    bridge_server_url: str
    client_id: str
    servers: List[ServerConfig]


def load_config(config_path: str = "config.json") -> Config:
    """加载配置文件"""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    servers = [
        ServerConfig(
            name=s["name"],
            command=s["command"],
            args=s["args"]
        )
        for s in data.get("servers", [])
    ]
    
    # 环境变量优先
    bridge_server_url = os.getenv("BRIDGE_SERVER_URL") or data["bridge_server_url"]
    client_id = os.getenv("CLIENT_ID") or data.get("client_id", "default-client")
    
    return Config(
        bridge_server_url=bridge_server_url,
        client_id=client_id,
        servers=servers
    )
