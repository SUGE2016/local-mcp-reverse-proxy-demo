"""Agent模块 - 智能体推理循环"""
import json
import logging
from typing import Dict, Any, List, AsyncGenerator

from openai import AsyncOpenAI

from mcp_client import MCPClient

logger = logging.getLogger(__name__)


class Agent:
    """智能体 - 处理用户消息并调用工具"""
    
    def __init__(self, openai_client: AsyncOpenAI, mcp_client: MCPClient, model: str = "gpt-4o-mini"):
        self.openai = openai_client
        self.mcp = mcp_client
        self.model = model
        self.max_iterations = 10  # 最大迭代次数，防止无限循环
    
    async def chat(self, user_message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """处理用户消息，返回流式响应"""
        # 获取可用工具
        tools = await self.mcp.list_tools()
        openai_tools = self.mcp.tools_to_openai_format(tools) if tools else None
        
        logger.info(f"可用工具数: {len(tools) if tools else 0}")
        
        # 初始化消息列表
        messages = [
            {"role": "system", "content": "你是一个有用的助手。你可以使用工具来帮助用户完成任务。"},
            {"role": "user", "content": user_message}
        ]
        
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            
            # 调用LLM
            response = await self.openai.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=openai_tools if openai_tools else None,
                tool_choice="auto" if openai_tools else None
            )
            
            assistant_message = response.choices[0].message
            
            # 检查是否有工具调用
            if assistant_message.tool_calls:
                # 添加助手消息
                messages.append(assistant_message)
                
                # 处理每个工具调用
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"调用工具: {function_name}")
                    
                    # 发送工具调用事件
                    yield {
                        "type": "tool_call",
                        "tool": function_name,
                        "arguments": function_args
                    }
                    
                    # 执行工具调用
                    result = await self.mcp.call_tool(function_name, function_args)
                    
                    # 发送工具结果事件
                    yield {
                        "type": "tool_result",
                        "tool": function_name,
                        "result": result
                    }
                    
                    # 添加工具结果到消息
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False)
                    })
            else:
                # 没有工具调用，返回最终响应
                yield {
                    "type": "message",
                    "content": assistant_message.content or ""
                }
                return
        
        # 超过最大迭代次数
        yield {
            "type": "error",
            "content": "超过最大迭代次数"
        }
