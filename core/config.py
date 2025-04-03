#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置管理模块，负责加载和处理配置文件。
"""

import json
import os
import logging
from typing import Any, Dict, Optional, Union

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("config")


class ConfigManager:
    """配置管理类，负责加载、处理和提供配置信息。"""

    def __init__(self, config_path: str = "config/config.json"):
        """
        初始化配置管理器。

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        """加载配置文件。"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            
            # 处理环境变量
            self._process_env_vars(self.config)
            
            # 设置日志级别
            log_level = self.get("server.log_level", "info").upper()
            logging.getLogger().setLevel(getattr(logging, log_level))
            
            logger.info(f"配置已加载: {self.config_path}")
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
            # 使用默认配置
            self.config = self._get_default_config()

    def _process_env_vars(self, config_dict: Dict[str, Any]) -> None:
        """
        处理配置中的环境变量。

        Args:
            config_dict: 配置字典
        """
        for key, value in config_dict.items():
            if isinstance(value, dict):
                self._process_env_vars(value)
            elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                config_dict[key] = os.environ.get(env_var, "")
                logger.debug(f"环境变量 {env_var} 替换为: {config_dict[key]}")

    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置。

        Returns:
            默认配置字典
        """
        return {
            "server": {
                "name": "template-mcp",
                "transport": "stdio",
                "log_level": "info",
                "debug": True
            },
            "plugins": {
                "directories": {
                    "resources": "plugins/resources",
                    "prompts": "plugins/prompts",
                    "tools": "plugins/tools",
                    "sampling": "plugins/sampling"
                },
                "hot_reload": False,
                "disabled": []
            }
        }

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置项。支持使用点号分隔的路径。

        Args:
            key_path: 配置项路径，如 "server.name"
            default: 默认值

        Returns:
            配置值
        """
        keys = key_path.split(".")
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
                
        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        设置配置项。支持使用点号分隔的路径。

        Args:
            key_path: 配置项路径，如 "server.name"
            value: 配置值
        """
        keys = key_path.split(".")
        config = self.config
        
        # 导航到最后一个键的父级
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
            
        # 设置最后一个键的值
        config[keys[-1]] = value

    def save(self) -> None:
        """保存配置到文件。"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存: {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")

    def get_plugin_directory(self, plugin_type: str) -> str:
        """
        获取插件目录路径。

        Args:
            plugin_type: 插件类型，如 "resources", "prompts", "tools", "sampling"

        Returns:
            插件目录路径
        """
        return self.get(f"plugins.directories.{plugin_type}", f"plugins/{plugin_type}")

    def is_plugin_disabled(self, plugin_id: str) -> bool:
        """
        检查插件是否被禁用。

        Args:
            plugin_id: 插件ID

        Returns:
            是否禁用
        """
        disabled = self.get("plugins.disabled", [])
        return plugin_id in disabled

    def get_tool_config(self, tool_id: str) -> Dict[str, Any]:
        """
        获取工具配置。

        Args:
            tool_id: 工具ID

        Returns:
            工具配置字典
        """
        return self.get(f"tool_configs.{tool_id}", {})


# 单例模式
config_manager = ConfigManager() 