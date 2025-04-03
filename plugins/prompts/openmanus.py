#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OpenManus风格的提示模板插件，提供各种任务场景的提示模板。
"""

import logging
import os
from typing import Dict, List, Optional, Any

# 尝试导入MCP类型
try:
    from mcp import types
    HAS_MCP_TYPES = True
except ImportError:
    HAS_MCP_TYPES = False

logger = logging.getLogger("openmanus_prompts")

def setup(mcp):
    """
    设置OpenManus风格的提示插件。
    
    Args:
        mcp: MCP服务器实例
    """
    logger.info("OpenManus提示模板插件初始化")
    
    @mcp.prompt()
    def general_assistant(directory=None) -> Dict[str, Any]:
        """
        通用助手提示模板，适用于多种任务场景。
        
        Args:
            directory: 初始工作目录，可选
            
        Returns:
            提示模板
        """
        current_dir = directory or os.getcwd()
        
        system_prompt = (
            "你是强大的AI助手，一个能力全面的智能工具，能够解决用户提出的各种任务。"
            "你拥有多种工具可以调用，能够高效完成复杂请求。无论是编程、信息检索、文件处理还是网页浏览，你都能胜任。"
            f"当前工作目录是: {current_dir}"
        )
        
        if HAS_MCP_TYPES:
            return types.GetPromptResult(
                description="通用AI助手提示",
                messages=[
                    types.PromptMessage(
                        role="system",
                        content=types.TextContent(
                            type="text", 
                            text=system_prompt
                        )
                    )
                ]
            )
        else:
            return {
                "description": "通用AI助手提示",
                "messages": [
                    {
                        "role": "system",
                        "content": {
                            "type": "text", 
                            "text": system_prompt
                        }
                    }
                ]
            }
    
    @mcp.prompt()
    def task_planning(task_description: str, steps: int = 5) -> Dict[str, Any]:
        """
        任务规划提示模板，帮助用户拆分任务并制定执行计划。
        
        Args:
            task_description: 任务描述
            steps: 计划步骤数，默认为5
            
        Returns:
            提示模板
        """
        system_prompt = (
            "你是一位资深任务规划专家，擅长将复杂任务分解为可执行的步骤，帮助用户高效完成工作。"
            "你需要考虑任务的依赖关系、可能的阻碍因素，并提供克服这些阻碍的建议。"
        )
        
        user_prompt = (
            f"我需要完成以下任务:\n\n{task_description}\n\n"
            f"请帮我将这个任务分解为{steps}个具体的执行步骤，包括:\n"
            "1. 每个步骤的具体目标\n"
            "2. 完成步骤所需的工具或资源\n"
            "3. 可能遇到的问题和解决方案\n"
            "4. 步骤成功的判断标准"
        )
        
        if HAS_MCP_TYPES:
            return types.GetPromptResult(
                description="任务规划助手",
                messages=[
                    types.PromptMessage(
                        role="system",
                        content=types.TextContent(
                            type="text", 
                            text=system_prompt
                        )
                    ),
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text", 
                            text=user_prompt
                        )
                    )
                ]
            )
        else:
            return {
                "description": "任务规划助手",
                "messages": [
                    {
                        "role": "system",
                        "content": {
                            "type": "text", 
                            "text": system_prompt
                        }
                    },
                    {
                        "role": "user",
                        "content": {
                            "type": "text", 
                            "text": user_prompt
                        }
                    }
                ]
            }
    
    @mcp.prompt()
    def code_assistant(language: str = "Python", project_description: Optional[str] = None) -> Dict[str, Any]:
        """
        代码助手提示模板，适用于编程和软件开发任务。
        
        Args:
            language: 编程语言，默认为Python
            project_description: 项目描述，可选
            
        Returns:
            提示模板
        """
        system_prompt = (
            f"你是一位专业的{language}开发者和问题解决者，擅长编写高质量、简洁且高效的代码。"
            f"你熟悉{language}的最佳实践、设计模式和性能优化技巧。"
            "你会提出明确的解决方案，并解释关键的设计决策。"
        )
        
        user_content = "我需要你的编程帮助。"
        if project_description:
            user_content = f"我正在开发这个项目: {project_description}\n\n请帮助我解决相关的编程问题。"
        
        if HAS_MCP_TYPES:
            return types.GetPromptResult(
                description=f"{language}编程助手",
                messages=[
                    types.PromptMessage(
                        role="system",
                        content=types.TextContent(
                            type="text", 
                            text=system_prompt
                        )
                    ),
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text", 
                            text=user_content
                        )
                    )
                ]
            )
        else:
            return {
                "description": f"{language}编程助手",
                "messages": [
                    {
                        "role": "system",
                        "content": {
                            "type": "text", 
                            "text": system_prompt
                        }
                    },
                    {
                        "role": "user",
                        "content": {
                            "type": "text", 
                            "text": user_content
                        }
                    }
                ]
            }
    
    @mcp.prompt()
    def browser_assistant() -> Dict[str, Any]:
        """
        浏览器自动化助手提示模板，适用于网页浏览和交互任务。
        
        Returns:
            提示模板
        """
        system_prompt = """你是一个设计用于自动化浏览器任务的AI代理。你的目标是按照规则完成最终任务。

# 输入格式
任务
之前的步骤
当前URL
打开的标签页
交互元素
[index]<type>text</type>
- index: 交互的数字标识符
- type: HTML元素类型(button, input等)
- text: 元素描述
示例:
[33]<button>提交表单</button>

- 只有带有[]中数字索引的元素才是可交互的
- 不带[]的元素仅提供上下文信息

# 响应规则
1. 当你看到"当前状态开始于此处"时，专注于以下内容：
   - 当前URL和页面标题
   - 可用的标签页
   - 交互元素及其索引
   - 视口上方或下方的内容（如有指示）
   - 任何操作结果或错误

2. 浏览器交互：
   - 导航：使用browser_use工具，action="go_to_url", url="..."
   - 点击：使用browser_use工具，action="click_element", index=N
   - 输入：使用browser_use工具，action="input_text", index=N, text="..."
   - 提取：使用browser_use工具，action="extract_content", goal="..."
   - 滚动：使用browser_use工具，action="scroll_down"或"scroll_up"

3. 考虑当前视口内外的内容，有条不紊地记住你的进度和学到的知识。"""
        
        if HAS_MCP_TYPES:
            return types.GetPromptResult(
                description="浏览器自动化助手",
                messages=[
                    types.PromptMessage(
                        role="system",
                        content=types.TextContent(
                            type="text", 
                            text=system_prompt
                        )
                    )
                ]
            )
        else:
            return {
                "description": "浏览器自动化助手",
                "messages": [
                    {
                        "role": "system",
                        "content": {
                            "type": "text", 
                            "text": system_prompt
                        }
                    }
                ]
            }

def teardown():
    """清理插件资源。"""
    logger.info("OpenManus提示模板插件已卸载") 