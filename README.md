# MCP Bridge Demo

一个 MCP（Model Context Protocol）反向代理系统演示，让远程 Web Agent 能够通过 Bridge 穿透 NAT 调用本地 MCP Server 的能力。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      远程服务器 (云端)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ web-frontend │  │  web-agent   │  │ mcp-bridge-server│   │
│  │   (React)    │◄─┤  (FastAPI)   │◄─┤    (FastAPI)     │   │
│  │   :3000      │  │    :8000     │  │      :8001       │   │
│  └──────────────┘  └──────────────┘  └────────┬─────────┘   │
└───────────────────────────────────────────────┼─────────────┘
                                                │ WebSocket
                                                │ (多路复用)
┌───────────────────────────────────────────────┼─────────────┐
│                    本地 (NAT 后面)              │             │
│  ┌──────────────────┐                         │             │
│  │ mcp-bridge-client├─────────────────────────┘             │
│  │    (Python)      │                                       │
│  └────────┬─────────┘                                       │
│           │ stdio                                           │
│  ┌────────┴─────────┐                                       │
│  │   MCP Servers    │                                       │
│  │ (filesystem等)   │                                       │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
```

## 核心特性

- **反向代理**：本地 MCP Server 无需公网 IP，通过 WebSocket 反向连接到云端
- **多路复用**：单一 WebSocket 连接支持多个 MCP Server
- **标准协议**：兼容 MCP 标准协议，可接入官方或第三方 MCP Server
- **智能体循环**：Web Agent 支持 LLM 工具调用的完整推理循环

## 快速开始

### 1. 克隆并安装依赖

```bash
git clone https://github.com/your-username/local-mcp-reverse-proxy-demo.git
cd local-mcp-reverse-proxy-demo

# 创建Python虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装Python依赖
pip install fastapi uvicorn websockets mcp httpx openai python-dotenv

# 安装前端依赖
cd web-frontend && npm install && cd ..
```

### 2. 配置

```bash
# 配置 LLM API（支持 OpenAI 兼容接口）
cd web-agent
cp .env.example .env
# 编辑 .env 文件，填入你的 API 配置
```

### 3. 启动服务

按以下顺序启动（每个命令在单独的终端中运行）：

```bash
# 激活虚拟环境（每个终端都需要）
source .venv/bin/activate

# 终端1: 启动 bridge-server (端口8001)
cd mcp-bridge-server && python main.py

# 终端2: 启动 bridge-client
cd mcp-bridge-client && python main.py

# 终端3: 启动 web-agent (端口8000)
cd web-agent && python main.py

# 终端4: 启动前端 (端口3000)
cd web-frontend && npm run dev
```

### 4. 访问

打开浏览器访问 http://localhost:3000

## 项目结构

```
local-mcp-reverse-proxy-demo/
├── mcp-bridge-server/     # 远程 Bridge 服务端
│   ├── main.py            # FastAPI 入口
│   ├── ws_handler.py      # WebSocket 处理
│   ├── registry.py        # 工具注册表
│   └── mcp_server.py      # MCP 接口
├── mcp-bridge-client/     # 本地 Bridge 客户端
│   ├── main.py            # 入口
│   ├── config.json        # MCP Server 配置
│   ├── mcp_manager.py     # MCP Server 进程管理
│   ├── ws_client.py       # WebSocket 客户端
│   └── simple_server.py   # 测试用 MCP Server
├── web-agent/             # Web Agent 后端
│   ├── main.py            # FastAPI 入口
│   ├── agent.py           # 智能体循环
│   └── mcp_client.py      # MCP 客户端
└── web-frontend/          # React 前端
    └── src/App.jsx        # 聊天界面
```

## 配置说明

### mcp-bridge-client/config.json

```json
{
  "bridge_server_url": "ws://localhost:8001/ws",
  "client_id": "local-client-1",
  "servers": [
    {
      "name": "test",
      "command": "python",
      "args": ["simple_server.py"]
    }
  ]
}
```

支持配置多个 MCP Server，工具名会自动加上 `{server_name}__` 前缀。

### web-agent/.env

```bash
# 支持 OpenAI 兼容接口
OPENAI_API_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4o-mini

BRIDGE_SERVER_URL=http://localhost:8001
```

## API 接口

### Bridge Server (8001)

| 接口 | 方法 | 说明 |
|------|------|------|
| `/ws` | WebSocket | Bridge Client 连接端点 |
| `/tools` | GET | 获取已注册工具列表 |
| `/tools/call` | POST | 调用工具 |
| `/clients` | GET | 获取已连接客户端 |

### Web Agent (8000)

| 接口 | 方法 | 说明 |
|------|------|------|
| `/chat` | POST | 聊天接口（SSE 流式响应） |
| `/chat/sync` | POST | 同步聊天接口 |
| `/tools` | GET | 获取可用工具 |

## 测试

默认配置使用内置的测试 MCP Server，提供两个工具：

- `test__echo` - 回显消息
- `test__get_time` - 获取当前时间

在聊天界面输入：
- "获取当前时间"
- "echo一下：Hello World"

### 使用官方 filesystem server

修改 `mcp-bridge-client/config.json`：

```json
{
  "servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./sandbox"]
    }
  ]
}
```

## License

MIT
