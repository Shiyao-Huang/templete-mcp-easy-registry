#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
插件加载器模块，负责扫描和加载插件。
"""

import importlib.util
import logging
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .config import config_manager

# 设置日志
logger = logging.getLogger("plugin_loader")


class PluginLoader:
    """插件加载器，负责扫描和加载符合约定的插件文件。"""

    def __init__(self, mcp: Any):
        """
        初始化插件加载器。

        Args:
            mcp: MCP服务器实例
        """
        self.mcp = mcp
        self.loaded_plugins: Dict[str, Any] = {}
        self.plugin_paths: Dict[str, str] = {}
        self.loaded_modules: Set[str] = set()

    def load_all_plugins(self) -> None:
        """加载所有类型的插件。"""
        plugin_types = ["resources", "prompts", "tools", "sampling"]
        
        for plugin_type in plugin_types:
            self.load_plugins_by_type(plugin_type)

    def load_plugins_by_type(self, plugin_type: str) -> None:
        """
        按类型加载插件。

        Args:
            plugin_type: 插件类型，如 "resources", "prompts", "tools", "sampling"
        """
        directory = config_manager.get_plugin_directory(plugin_type)
        
        if not os.path.exists(directory):
            logger.warning(f"插件目录不存在: {directory}")
            return
        
        logger.info(f"加载{plugin_type}插件...")
        
        # 遍历目录中的所有Python文件
        for filename in os.listdir(directory):
            if filename.endswith(".py") and not filename.startswith("__"):
                plugin_id = filename[:-3]  # 去掉.py扩展名
                
                # 检查插件是否被禁用
                if config_manager.is_plugin_disabled(plugin_id):
                    logger.info(f"跳过已禁用的插件: {plugin_id}")
                    continue
                
                file_path = os.path.join(directory, filename)
                self._load_plugin_file(plugin_id, file_path, plugin_type)

    def _load_plugin_file(self, plugin_id: str, file_path: str, plugin_type: str) -> None:
        """
        加载单个插件文件。

        Args:
            plugin_id: 插件ID
            file_path: 插件文件路径
            plugin_type: 插件类型
        """
        try:
            # 创建模块名称（确保唯一性）
            module_name = f"{plugin_type}.{plugin_id}"
            
            # 如果模块已加载，则跳过
            if module_name in self.loaded_modules:
                logger.debug(f"模块已加载: {module_name}")
                return
            
            # 动态导入模块
            logger.debug(f"导入模块: {module_name} 从 {file_path}")
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None:
                logger.error(f"无法加载插件文件: {file_path}")
                return
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 调用插件的setup函数
            if hasattr(module, 'setup'):
                logger.debug(f"调用插件{plugin_id}的setup函数")
                module.setup(self.mcp)
                self.loaded_plugins[plugin_id] = module
                self.plugin_paths[plugin_id] = file_path
                self.loaded_modules.add(module_name)
                logger.info(f"成功加载插件: {plugin_id} ({plugin_type})")
            else:
                logger.warning(f"插件{plugin_id}没有setup函数")
        except Exception as e:
            logger.error(f"加载插件{plugin_id}失败: {str(e)}", exc_info=True)

    def reload_plugin(self, plugin_id: str) -> bool:
        """
        重新加载插件。

        Args:
            plugin_id: 插件ID

        Returns:
            是否成功重新加载
        """
        if plugin_id not in self.loaded_plugins or plugin_id not in self.plugin_paths:
            logger.warning(f"插件未加载，无法重新加载: {plugin_id}")
            return False
        
        try:
            file_path = self.plugin_paths[plugin_id]
            # 确定插件类型
            plugin_type = None
            for t in ["resources", "prompts", "tools", "sampling"]:
                if file_path.startswith(config_manager.get_plugin_directory(t)):
                    plugin_type = t
                    break
            
            if not plugin_type:
                logger.error(f"无法确定插件类型: {plugin_id}")
                return False
            
            # 从已加载模块中删除
            module_name = f"{plugin_type}.{plugin_id}"
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            # 从已加载插件中删除
            if plugin_id in self.loaded_plugins:
                del self.loaded_plugins[plugin_id]
            
            if module_name in self.loaded_modules:
                self.loaded_modules.remove(module_name)
            
            # 重新加载
            self._load_plugin_file(plugin_id, file_path, plugin_type)
            logger.info(f"插件已重新加载: {plugin_id}")
            return True
        except Exception as e:
            logger.error(f"重新加载插件{plugin_id}失败: {str(e)}", exc_info=True)
            return False

    def get_loaded_plugins(self) -> Dict[str, Any]:
        """
        获取已加载的插件列表。

        Returns:
            已加载插件字典
        """
        return self.loaded_plugins.copy()

    def unload_plugin(self, plugin_id: str) -> bool:
        """
        卸载插件。

        Args:
            plugin_id: 插件ID

        Returns:
            是否成功卸载
        """
        if plugin_id not in self.loaded_plugins:
            logger.warning(f"插件未加载，无法卸载: {plugin_id}")
            return False
        
        try:
            # 调用插件的teardown函数（如果存在）
            module = self.loaded_plugins[plugin_id]
            if hasattr(module, 'teardown'):
                module.teardown()
            
            # 从已加载插件中删除
            del self.loaded_plugins[plugin_id]
            
            # 确定模块名称并删除
            file_path = self.plugin_paths[plugin_id]
            for t in ["resources", "prompts", "tools", "sampling"]:
                module_name = f"{t}.{plugin_id}"
                if module_name in sys.modules:
                    del sys.modules[module_name]
                if module_name in self.loaded_modules:
                    self.loaded_modules.remove(module_name)
            
            del self.plugin_paths[plugin_id]
            
            logger.info(f"插件已卸载: {plugin_id}")
            return True
        except Exception as e:
            logger.error(f"卸载插件{plugin_id}失败: {str(e)}", exc_info=True)
            return False 