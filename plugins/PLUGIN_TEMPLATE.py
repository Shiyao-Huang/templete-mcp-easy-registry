#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
插件模板，作为开发新插件的参考。
根据插件类型，放置在对应的目录：resources/、prompts/、tools/或sampling/
"""

import logging

# 创建日志器，插件名应与文件名匹配（不包括.py扩展名）
logger = logging.getLogger("plugin_name")

def setup(mcp):
    """
    设置插件。这是每个插件必须实现的入口函数。
    
    Args:
        mcp: MCP服务器实例，提供resource()、prompt()、tool()等装饰器
    """
    logger.info("插件初始化")
    
    # 获取插件配置（如果需要）
    # config = mcp.config.get("tool_configs", {}).get("plugin_name", {})
    # some_setting = config.get("some_setting", "default_value")
    
    # === 资源插件示例 ===
    # @mcp.resource("example://{param}")
    # def example_resource(param):
    #     """提供示例资源。"""
    #     return f"这是示例资源: {param}"
    
    # === 提示插件示例 ===
    # @mcp.prompt()
    # def example_prompt(param1, param2="默认值"):
    #     """提供示例提示模板。"""
    #     return {
    #         "description": "示例提示",
    #         "messages": [
    #             {
    #                 "role": "system",
    #                 "content": {
    #                     "type": "text", 
    #                     "text": "系统提示内容"
    #                 }
    #             },
    #             {
    #                 "role": "user",
    #                 "content": {
    #                     "type": "text", 
    #                     "text": f"用户提示，参数: {param1}, {param2}"
    #                 }
    #             }
    #         ]
    #     }
    
    # === 工具插件示例 ===
    # @mcp.tool()
    # def example_tool(param1, param2=None):
    #     """执行示例工具操作。"""
    #     try:
    #         # 工具逻辑
    #         result = f"操作结果: {param1}, {param2}"
    #         return {"result": result, "status": "success"}
    #     except Exception as e:
    #         logger.error(f"工具执行错误: {str(e)}")
    #         return {"error": str(e), "status": "error"}
    
    # === 采样插件示例 ===
    # async def example_sampling_handler(request):
    #     """处理采样请求。"""
    #     prompt = request.get('prompt', '')
    #     system_prompt = request.get('systemPrompt', '')
    #     options = request.get('options', {})
    #     
    #     # 处理采样逻辑
    #     return f"采样响应: {prompt}"
    # 
    # # 注册采样回调
    # mcp.sampling_callback = example_sampling_handler

def teardown():
    """
    清理插件资源。
    这个函数是可选的，但建议实现，尤其是需要释放资源的插件。
    """
    logger.info("插件资源清理")
    # 在这里释放资源、关闭连接等 