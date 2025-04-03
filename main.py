#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCP服务器主入口程序，负责加载配置、初始化服务器和插件。
"""

import os
import sys
import json
import logging
import argparse
import importlib.util
from pathlib import Path

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("mcp_server")

# 尝试导入MCP库
try:
    from mcp.server import MCPServer
except ImportError:
    logger.error("找不到MCP库，请确保已安装Python MCP SDK")
    logger.info("可以通过 pip install mcp-python-sdk 安装")
    sys.exit(1)

def load_config(config_path):
    """
    加载配置文件。
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        配置字典
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {str(e)}")
        return {}

def discover_plugins(plugins_dir):
    """
    发现可用插件。
    
    Args:
        plugins_dir: 插件目录
        
    Returns:
        插件模块列表
    """
    plugins = []
    
    # 插件类型
    plugin_types = ["resources", "tools", "prompts", "samplers"]
    
    for plugin_type in plugin_types:
        type_dir = os.path.join(plugins_dir, plugin_type)
        
        if not os.path.exists(type_dir):
            logger.warning(f"插件目录不存在: {type_dir}")
            continue
        
        # 遍历插件类型目录下的所有Python文件
        for file in os.listdir(type_dir):
            if file.endswith(".py") and not file.startswith("__"):
                plugin_path = os.path.join(type_dir, file)
                
                try:
                    # 动态加载模块
                    module_name = f"{plugin_type}.{file[:-3]}"
                    spec = importlib.util.spec_from_file_location(module_name, plugin_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # 检查模块是否有必要的函数
                    if hasattr(module, "setup"):
                        plugins.append((module, plugin_type))
                        logger.debug(f"发现插件: {module_name}")
                    else:
                        logger.warning(f"跳过插件 {module_name}: 缺少setup函数")
                        
                except Exception as e:
                    logger.error(f"加载插件 {plugin_path} 失败: {str(e)}")
    
    return plugins

def initialize_server(config):
    """
    初始化MCP服务器。
    
    Args:
        config: 服务器配置
        
    Returns:
        MCPServer实例
    """
    server_config = config.get("server", {})
    host = server_config.get("host", "127.0.0.1")
    port = server_config.get("port", 8080)
    
    # 创建服务器实例
    server = MCPServer(
        host=host,
        port=port,
        config=config
    )
    
    return server

def load_plugins(server, plugins):
    """
    加载插件到服务器。
    
    Args:
        server: MCPServer实例
        plugins: 插件模块列表
    """
    for module, plugin_type in plugins:
        try:
            # 调用插件的setup函数
            module.setup(server)
            logger.info(f"已加载 {plugin_type} 插件: {module.__name__}")
        except Exception as e:
            logger.error(f"初始化插件 {module.__name__} 失败: {str(e)}")

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="MCP服务器")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--plugins", default="plugins", help="插件目录")
    parser.add_argument("--debug", action="store_true", help="启用调试日志")
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 获取配置和插件目录的绝对路径
    config_path = os.path.abspath(args.config)
    plugins_dir = os.path.abspath(args.plugins)
    
    logger.info(f"启动MCP服务器")
    logger.info(f"配置文件: {config_path}")
    logger.info(f"插件目录: {plugins_dir}")
    
    # 加载配置
    config = load_config(config_path)
    
    # 发现可用插件
    plugins = discover_plugins(plugins_dir)
    logger.info(f"发现 {len(plugins)} 个可用插件")
    
    # 初始化服务器
    server = initialize_server(config)
    
    # 加载插件
    load_plugins(server, plugins)
    
    # 启动服务器
    try:
        logger.info(f"服务器正在启动: {server.host}:{server.port}")
        server.start()
    except KeyboardInterrupt:
        logger.info("接收到终止信号，正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器运行错误: {str(e)}")
    finally:
        # 清理资源
        server.stop()
        logger.info("服务器已关闭")

if __name__ == "__main__":
    main() 