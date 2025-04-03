#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCP服务器实现，基于MCP SDK提供即插即用能力。
"""

import asyncio
import atexit
import logging
import os
import signal
import sys
from typing import Any, Callable, Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP

from .config import config_manager
from .plugin_loader import PluginLoader

# 设置日志
logger = logging.getLogger("mcp_server")


class MCPServer:
    """MCP服务器类，基于MCP SDK实现，支持即插即用能力。"""

    def __init__(self, name: Optional[str] = None, config_path: Optional[str] = None):
        """
        初始化MCP服务器。

        Args:
            name: 服务器名称，默认从配置中读取
            config_path: 配置文件路径，默认为"config/config.json"
        """
        # 如果提供了配置路径，重新加载配置
        if config_path:
            global config_manager
            from .config import ConfigManager
            config_manager = ConfigManager(config_path)
        
        # 从配置中获取服务器名称，或使用传入的名称
        self.name = name or config_manager.get("server.name", "template-mcp")
        
        # 创建FastMCP实例
        self.mcp = FastMCP(self.name)
        
        # 将配置添加为MCP实例的属性，方便插件访问
        self.mcp.config = config_manager.config
        
        # 创建插件加载器
        self.plugin_loader = PluginLoader(self.mcp)
        
        # 注册清理函数
        atexit.register(self.cleanup)
        
        # 启用热加载（如果配置中启用）
        if config_manager.get("plugins.hot_reload", False):
            self._setup_hot_reload()
        
        # 初始化内部存储，供插件使用
        self.mcp._storage = {}

    def load_plugins(self) -> None:
        """加载所有插件。"""
        logger.info("开始加载插件...")
        self.plugin_loader.load_all_plugins()
        logger.info("插件加载完成")

    def run(self, transport: Optional[str] = None) -> None:
        """
        运行MCP服务器。

        Args:
            transport: 传输方式，默认从配置中读取
        """
        # 加载插件
        self.load_plugins()
        
        # 确定传输方式
        if transport is None:
            transport = config_manager.get("server.transport", "stdio")
        
        # 注册信号处理函数（用于优雅退出）
        self._register_signal_handlers()
        
        # 启动服务器
        logger.info(f"启动MCP服务器 {self.name}，传输方式：{transport}")
        try:
            self.mcp.run(transport=transport)
        except Exception as e:
            logger.error(f"服务器运行错误: {str(e)}", exc_info=True)
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """清理服务器资源。"""
        logger.info("清理服务器资源...")
        # 这里可以添加一些清理逻辑，例如关闭连接等
        
        # 如果atexit已注册，则取消注册（防止重复调用）
        if hasattr(self, "_cleanup_registered") and self._cleanup_registered:
            try:
                atexit.unregister(self.cleanup)
                self._cleanup_registered = False
            except Exception:
                pass

    def _register_signal_handlers(self) -> None:
        """注册信号处理函数，用于优雅退出。"""
        try:
            # SIGINT（Ctrl+C）
            signal.signal(signal.SIGINT, self._signal_handler)
            # SIGTERM（终止信号）
            signal.signal(signal.SIGTERM, self._signal_handler)
            logger.debug("信号处理函数已注册")
        except Exception:
            logger.warning("无法注册信号处理函数")

    def _signal_handler(self, sig: int, frame: Any) -> None:
        """
        信号处理函数。

        Args:
            sig: 信号类型
            frame: 栈帧
        """
        logger.info(f"接收到信号 {sig}，准备退出...")
        self.cleanup()
        sys.exit(0)

    def _setup_hot_reload(self) -> None:
        """设置插件热加载。"""
        # 这里简单实现热加载，真实场景可能需要使用watchdog等库
        logger.info("启用插件热加载")
        
        # 创建一个简单的轮询器，定期检查文件变更
        # 注意：这不是性能最优的方案，生产环境应使用专门的文件监视库
        async def _watch_files():
            plugin_dirs = [
                config_manager.get_plugin_directory(t)
                for t in ["resources", "prompts", "tools", "sampling"]
            ]
            
            # 存储文件修改时间
            file_mtimes = {}
            
            while True:
                try:
                    for directory in plugin_dirs:
                        if not os.path.exists(directory):
                            continue
                            
                        for filename in os.listdir(directory):
                            if filename.endswith(".py") and not filename.startswith("__"):
                                file_path = os.path.join(directory, filename)
                                plugin_id = filename[:-3]  # 去掉.py扩展名
                                
                                # 获取文件修改时间
                                try:
                                    mtime = os.path.getmtime(file_path)
                                    
                                    # 如果文件是新的或被修改了
                                    if file_path not in file_mtimes or file_mtimes[file_path] != mtime:
                                        file_mtimes[file_path] = mtime
                                        
                                        # 如果插件已加载，则重新加载
                                        if plugin_id in self.plugin_loader.loaded_plugins:
                                            logger.info(f"检测到插件变更: {plugin_id}，重新加载")
                                            self.plugin_loader.reload_plugin(plugin_id)
                                        # 否则加载新插件
                                        else:
                                            # 确定插件类型
                                            plugin_type = None
                                            for t in ["resources", "prompts", "tools", "sampling"]:
                                                if directory == config_manager.get_plugin_directory(t):
                                                    plugin_type = t
                                                    break
                                                    
                                            if plugin_type:
                                                logger.info(f"检测到新插件: {plugin_id} ({plugin_type})，加载")
                                                self.plugin_loader._load_plugin_file(plugin_id, file_path, plugin_type)
                                except Exception as e:
                                    logger.error(f"检查文件{file_path}时出错: {str(e)}")
                except Exception as e:
                    logger.error(f"热加载检查时出错: {str(e)}")
                    
                # 每5秒检查一次
                await asyncio.sleep(5)
                
        # 创建后台任务
        loop = asyncio.get_event_loop()
        try:
            loop.create_task(_watch_files())
            logger.debug("热加载监视器已启动")
        except Exception as e:
            logger.error(f"启动热加载监视器失败: {str(e)}")


# 创建服务器实例的工厂函数
def create_server(name: Optional[str] = None, config_path: Optional[str] = None) -> MCPServer:
    """
    创建MCP服务器实例。

    Args:
        name: 服务器名称
        config_path: 配置文件路径

    Returns:
        MCPServer实例
    """
    return MCPServer(name, config_path) 