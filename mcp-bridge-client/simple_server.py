"""简单的MCP Server用于测试"""
import asyncio
import json
import sys
from datetime import datetime


async def handle_request(request):
    """处理MCP请求"""
    method = request.get("method")
    req_id = request.get("id")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "simple-test-server", "version": "1.0.0"}
            }
        }
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "echo",
                        "description": "Echo back the input message",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string", "description": "Message to echo"}
                            },
                            "required": ["message"]
                        }
                    },
                    {
                        "name": "get_time",
                        "description": "Get current time",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
            }
        }
    
    elif method == "tools/call":
        tool_name = request.get("params", {}).get("name")
        args = request.get("params", {}).get("arguments", {})
        
        if tool_name == "echo":
            result_text = f"Echo: {args.get('message', '')}"
        elif tool_name == "get_time":
            result_text = f"Current time: {datetime.now().isoformat()}"
        else:
            result_text = f"Unknown tool: {tool_name}"
        
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": result_text}]
            }
        }
    
    elif method == "notifications/initialized":
        # 通知，不需要响应
        return None
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }


async def main():
    """主循环 - 从stdin读取请求，写响应到stdout"""
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
    
    writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, asyncio.get_event_loop())
    
    buffer = ""
    
    while True:
        try:
            chunk = await reader.read(4096)
            if not chunk:
                break
            
            buffer += chunk.decode()
            
            # 尝试解析JSON-RPC消息
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                    response = await handle_request(request)
                    if response:
                        response_str = json.dumps(response) + "\n"
                        writer.write(response_str.encode())
                        await writer.drain()
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            break


if __name__ == "__main__":
    asyncio.run(main())
