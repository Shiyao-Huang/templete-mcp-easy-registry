#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
规划提示插件，提供任务规划的提示模板。
"""

import logging

logger = logging.getLogger("planning_prompt")

def setup(mcp):
    """
    设置规划提示插件。
    
    Args:
        mcp: MCP服务器实例
    """
    logger.info("规划提示插件初始化")
    
    @mcp.prompt()
    def task_planning(task, steps=5, expertise_level="专业"):
        """
        生成任务规划提示。
        
        Args:
            task: 要规划的任务
            steps: 规划步骤数，默认为5
            expertise_level: 专业水平，可选"初级"、"中级"、"专业"、"专家"
            
        Returns:
            提示模板
        """
        logger.debug(f"生成任务规划提示: task={task}, steps={steps}, level={expertise_level}")
        
        # 根据专业水平调整系统提示
        system_prompts = {
            "初级": "你是一个帮助初学者的任务规划助手，擅长将复杂任务分解为简单、易于理解的步骤。",
            "中级": "你是一个有经验的任务规划助手，擅长将任务分解为明确、可执行的步骤。",
            "专业": "你是一个专业的任务规划助手，擅长将复杂任务分解为高效、优化的步骤，并考虑潜在风险。",
            "专家": "你是一个专家级任务规划助手，擅长将复杂任务分解为精确、深入的步骤，同时评估每一步的资源需求、风险和替代方案。"
        }
        
        system_prompt = system_prompts.get(expertise_level, system_prompts["专业"])
        
        return {
            "description": f"任务规划提示（{expertise_level}级）",
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
                        "text": f"请为以下任务制定一个包含{steps}个步骤的详细计划：\n\n{task}\n\n" +
                                f"对于每个步骤，请提供：\n" +
                                f"1. 步骤名称\n" +
                                f"2. 详细说明\n" +
                                f"3. 预期结果\n" +
                                f"4. 可能遇到的问题及解决方案"
                    }
                }
            ]
        }
    
    @mcp.prompt()
    def code_planning(project_description, language="Python"):
        """
        生成代码项目规划提示。
        
        Args:
            project_description: 项目描述
            language: 编程语言，默认为Python
            
        Returns:
            提示模板
        """
        logger.debug(f"生成代码规划提示: project={project_description}, language={language}")
        
        return {
            "description": f"{language}项目规划",
            "messages": [
                {
                    "role": "system",
                    "content": {
                        "type": "text", 
                        "text": f"你是一个专业的{language}开发规划师，擅长设计软件架构和规划开发步骤。"
                    }
                },
                {
                    "role": "user",
                    "content": {
                        "type": "text", 
                        "text": f"我需要开发一个{language}项目，描述如下：\n\n{project_description}\n\n" +
                                f"请提供：\n" +
                                f"1. 项目架构设计\n" +
                                f"2. 核心模块划分\n" +
                                f"3. 数据模型设计\n" +
                                f"4. 开发步骤规划\n" +
                                f"5. 关键API和函数设计\n" +
                                f"6. 可能的技术挑战及解决思路"
                    }
                }
            ]
        }

def teardown():
    """清理插件资源。"""
    logger.info("规划提示插件已卸载") 