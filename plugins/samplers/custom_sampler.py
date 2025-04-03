#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自定义采样器插件，用于处理模型调用和文本生成。
支持MCP服务器向客户端请求采样，实现递归对话和代理行为。
"""

import logging
import json
import os
import asyncio
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger("custom_sampler")

def setup(mcp):
    """
    设置自定义采样器插件。
    
    Args:
        mcp: MCP服务器实例
    """
    logger.info("自定义采样器插件初始化")
    
    # 获取配置信息
    config = mcp.get_config().get("custom_sampler", {})
    default_temperature = config.get("default_temperature", 0.7)
    default_max_tokens = config.get("default_max_tokens", 1000)
    
    # 如果客户端支持采样能力，使用request_sampling方法请求LLM采样
    # 这个函数可以被其他工具或资源调用
    async def request_sampling(prompt: str, system_prompt: Optional[str] = None, 
                            options: Optional[Dict[str, Any]] = None) -> str:
        """
        向客户端请求LLM采样，用于递归对话和代理行为。
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示，可选
            options: 采样选项，如温度和最大令牌数
            
        Returns:
            LLM生成的回复
        """
        sampling_request = {
            "prompt": prompt
        }
        
        if system_prompt:
            sampling_request["systemPrompt"] = system_prompt
        
        if options:
            sampling_request["options"] = options
        else:
            sampling_request["options"] = {
                "temperature": default_temperature,
                "maxTokens": default_max_tokens
            }
        
        try:
            # 调用MCP服务器的request_sampling方法
            # 这是MCP协议中客户端到服务器的采样请求
            logger.info(f"发送采样请求: prompt='{prompt[:50]}...'")
            sampling_result = await mcp.request_sampling(sampling_request)
            logger.info("采样请求已完成")
            return sampling_result
        except Exception as e:
            logger.error(f"采样请求失败: {str(e)}")
            return f"采样请求失败: {str(e)}"
    
    # 将request_sampling函数导出为插件
    mcp.register_plugin("request_sampling", request_sampling)
    
    # 创建采样工具
    @mcp.tool()
    async def generate_content(prompt: str, system_prompt: Optional[str] = None, 
                           temperature: float = default_temperature) -> Dict[str, Any]:
        """
        生成文本内容的工具，使用MCP采样能力。
        
        Args:
            prompt: 生成提示
            system_prompt: 系统提示，可选
            temperature: 温度参数，控制创造性，默认为配置中的值
            
        Returns:
            生成的内容结果
        """
        try:
            options = {
                "temperature": temperature,
                "maxTokens": default_max_tokens
            }
            
            # 调用request_sampling函数
            result = await request_sampling(prompt, system_prompt, options)
            
            return {
                "generated_content": result,
                "prompt": prompt,
                "temperature": temperature
            }
        except Exception as e:
            logger.error(f"内容生成失败: {str(e)}")
            return {
                "error": f"内容生成失败: {str(e)}",
                "prompt": prompt
            }
    
    # 设置标准的采样处理函数
    # 这个函数处理客户端到服务器的采样请求，但实际使用方式是服务器到客户端的请求
    @mcp.sampler()
    async def sample(client_instance, messages, tools=None, tool_choice=None, context=None):
        """
        处理采样请求，从LLM获取响应。
        此函数一般不会被直接调用，因为MCP通常是服务器向客户端请求采样。
        
        Args:
            client_instance: MCP客户端实例
            messages: 消息历史
            tools: 可用工具列表
            tool_choice: 工具选择参数
            context: 上下文信息
            
        Returns:
            采样结果
        """
        logger.debug(f"接收到采样请求: {len(messages)} 条消息")
        
        try:
            # 提取消息内容
            formatted_messages = _format_messages(messages)
            
            # 准备工具信息
            formatted_tools = None
            if tools:
                formatted_tools = _format_tools(tools)
                logger.debug(f"格式化了 {len(formatted_tools)} 个工具")
            
            # 使用客户端实例调用采样方法
            # 通常，这个函数不会被直接调用，因为在MCP流程中客户端会请求服务器提供工具、资源等，
            # 而服务器会请求客户端提供采样能力
            logger.warning("收到直接采样请求，这通常不符合MCP协议的常见流程。")
            logger.warning("MCP协议一般是服务器使用request_sampling向客户端请求采样。")
            
            # 尝试调用客户端的sample方法
            if hasattr(client_instance, "sample"):
                params = {
                    "messages": formatted_messages
                }
                
                if formatted_tools:
                    params["tools"] = formatted_tools
                
                if tool_choice:
                    params["tool_choice"] = tool_choice
                
                return await client_instance.sample(**params)
            
            # 返回错误信息
            return {
                "type": "text",
                "text": "采样器无法调用模型。请使用request_sampling方法向客户端请求采样。"
            }
            
        except Exception as e:
            logger.error(f"采样过程出错: {str(e)}")
            return {
                "type": "text",
                "text": f"生成响应时出错: {str(e)}"
            }

def _format_messages(messages):
    """
    格式化消息以适应LLM的输入格式。
    
    Args:
        messages: 原始消息列表
        
    Returns:
        格式化的消息列表
    """
    formatted_messages = []
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", [])
        
        # 处理多部分内容
        if isinstance(content, list):
            formatted_content = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        formatted_content.append(part)
                    # 可以在这里添加处理其他类型的逻辑
                else:
                    # 如果是字符串，转换为text类型
                    formatted_content.append({"type": "text", "text": str(part)})
            
            formatted_messages.append({
                "role": role,
                "content": formatted_content
            })
        else:
            # 如果内容是字符串，简单转换
            formatted_messages.append({
                "role": role,
                "content": [{"type": "text", "text": str(content)}]
            })
    
    return formatted_messages

def _format_tools(tools):
    """
    格式化工具以适应LLM的输入格式。
    
    Args:
        tools: 原始工具列表
        
    Returns:
        格式化的工具列表
    """
    formatted_tools = []
    
    for tool in tools:
        # 基本工具数据
        formatted_tool = {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {})
            }
        }
        
        formatted_tools.append(formatted_tool)
    
    return formatted_tools

def teardown():
    """清理插件资源。"""
    logger.info("自定义采样器插件已卸载") 