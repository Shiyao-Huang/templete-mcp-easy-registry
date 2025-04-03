#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件资源插件，提供从本地文件系统读取和解析文件的能力。
"""

import logging
import os
import json
import yaml
from pathlib import Path

logger = logging.getLogger("file_resource")

# 定义支持的文件类型和对应的解析处理函数
FILE_HANDLERS = {
    ".txt": lambda content: content,
    ".md": lambda content: content,
    ".json": lambda content: json.loads(content),
    ".yaml": lambda content: yaml.safe_load(content),
    ".yml": lambda content: yaml.safe_load(content),
}

def setup(mcp):
    """
    设置文件资源插件。
    
    Args:
        mcp: MCP服务器实例
    """
    logger.info("文件资源插件初始化")
    
    # 获取配置信息
    config = mcp.get_config().get("file_resource", {})
    base_dir = config.get("base_dir", os.path.join(os.path.dirname(__file__), "../../data"))
    
    # 确保基础目录存在
    base_dir = os.path.abspath(base_dir)
    os.makedirs(base_dir, exist_ok=True)
    
    logger.info(f"文件资源基础目录: {base_dir}")
    
    @mcp.resource("file://{path}")
    async def file_resource(path):
        """
        读取文件内容的资源处理函数。
        
        Args:
            path: 文件路径，相对于基础目录
            
        Returns:
            文件内容，根据文件类型可能会进行解析
            
        Raises:
            ValueError: 当文件不存在或路径无效时
        """
        # 安全检查：防止路径遍历攻击
        if ".." in path or path.startswith("/"):
            raise ValueError(f"无效的文件路径: {path}")
        
        file_path = os.path.join(base_dir, path)
        file_path = os.path.normpath(file_path)
        
        # 确保文件在基础目录内
        if not file_path.startswith(base_dir):
            raise ValueError(f"文件路径必须在基础目录内: {path}")
        
        if not os.path.exists(file_path):
            raise ValueError(f"文件不存在: {path}")
        
        if not os.path.isfile(file_path):
            raise ValueError(f"路径不是一个文件: {path}")
        
        # 读取文件内容
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # 获取MIME类型
            file_ext = os.path.splitext(file_path)[1].lower()
            mime_type = "text/plain"
            if file_ext == ".md":
                mime_type = "text/markdown"
            elif file_ext == ".json":
                mime_type = "application/json"
            elif file_ext in [".yaml", ".yml"]:
                mime_type = "application/yaml"
            
            # 根据文件扩展名处理内容
            if file_ext in FILE_HANDLERS:
                try:
                    parsed_content = FILE_HANDLERS[file_ext](content)
                    # 返回MCP规范的资源响应格式
                    return {
                        "uri": f"file://{path}",
                        "mimeType": mime_type,
                        "text": content,
                        # 对于解析后的内容，添加一个额外的字段
                        "parsed": parsed_content if parsed_content != content else None
                    }
                except Exception as e:
                    logger.warning(f"处理文件内容时出错 {file_path}: {str(e)}")
            
            # 默认返回文本内容
            return {
                "uri": f"file://{path}",
                "mimeType": mime_type,
                "text": content
            }
        except Exception as e:
            logger.error(f"读取文件时出错 {file_path}: {str(e)}")
            raise ValueError(f"读取文件时出错: {str(e)}")
    
    @mcp.resource("dir://{directory}")
    async def directory_resource(directory=""):
        """
        列出指定目录下的文件和子目录。
        
        Args:
            directory: 相对于基础目录的子目录路径
            
        Returns:
            包含文件和目录列表的资源
        """
        # 安全检查：防止路径遍历攻击
        if ".." in directory or directory.startswith("/"):
            raise ValueError(f"无效的目录路径: {directory}")
        
        dir_path = os.path.join(base_dir, directory)
        dir_path = os.path.normpath(dir_path)
        
        # 确保目录在基础目录内
        if not dir_path.startswith(base_dir):
            raise ValueError(f"目录路径必须在基础目录内: {directory}")
        
        if not os.path.exists(dir_path):
            raise ValueError(f"目录不存在: {directory}")
        
        if not os.path.isdir(dir_path):
            raise ValueError(f"路径不是一个目录: {directory}")
        
        try:
            files = []
            dirs = []
            
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                if os.path.isfile(item_path):
                    files.append(item)
                elif os.path.isdir(item_path):
                    dirs.append(item)
            
            # 按照规范格式返回目录内容
            directory_content = {
                "current_directory": directory or "/",
                "files": [{"name": f, "uri": f"file://{os.path.join(directory, f)}"} for f in files],
                "directories": [{"name": d, "uri": f"dir://{os.path.join(directory, d)}"} for d in dirs]
            }
            
            return {
                "uri": f"dir://{directory}",
                "mimeType": "inode/directory",
                "text": json.dumps(directory_content, indent=2)
            }
        except Exception as e:
            logger.error(f"列出目录内容时出错 {dir_path}: {str(e)}")
            raise ValueError(f"列出目录内容时出错: {str(e)}")

def teardown():
    """清理插件资源。"""
    logger.info("文件资源插件已卸载") 