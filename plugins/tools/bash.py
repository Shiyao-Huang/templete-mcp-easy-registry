#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bash工具插件，提供安全的Bash命令执行功能。
"""

import logging
import re
import subprocess
import shlex
import os

logger = logging.getLogger("bash_tool")

def setup(mcp):
    """
    设置Bash工具插件。
    
    Args:
        mcp: MCP服务器实例
    """
    # 获取插件配置
    config = mcp.config.get("tool_configs", {}).get("bash", {})
    allowed_commands = config.get("allowed_commands", ["ls", "cat", "echo", "grep", "find"])
    enabled = config.get("enabled", True)
    
    logger.info(f"Bash工具插件初始化: 已启用 = {enabled}, 允许的命令 = {allowed_commands}")
    
    if not enabled:
        logger.info("Bash工具插件已禁用")
        return
    
    @mcp.tool()
    def bash(command):
        """
        执行Bash命令。
        
        Args:
            command: 要执行的Bash命令
            
        Returns:
            命令执行结果或错误消息
        """
        logger.debug(f"执行Bash命令: {command}")
        
        try:
            # 安全检查
            if not is_safe_command(command, allowed_commands):
                logger.warning(f"检测到不安全的命令: {command}")
                return {
                    "error": "不安全的命令，仅支持有限的基本命令",
                    "allowed_commands": allowed_commands
                }
            
            # 执行命令
            result = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                text=True
            )
            
            # 处理结果
            stdout = result.stdout
            stderr = result.stderr
            
            logger.debug(f"命令执行完成: 退出码 = {result.returncode}")
            
            return {
                "output": stdout,
                "error": stderr,
                "return_code": result.returncode,
                "command": command
            }
        except subprocess.TimeoutExpired:
            logger.error(f"命令执行超时: {command}")
            return {
                "error": "命令执行超时（限制为10秒）",
                "command": command
            }
        except Exception as e:
            logger.error(f"命令执行失败: {str(e)}")
            return {
                "error": f"命令执行失败: {str(e)}",
                "command": command
            }
    
    @mcp.tool()
    def ls(path="."):
        """
        列出目录内容。
        
        Args:
            path: 要列出内容的目录路径，默认为当前目录
            
        Returns:
            目录内容列表或错误消息
        """
        logger.debug(f"列出目录内容: {path}")
        
        try:
            # 安全检查
            if not is_safe_path(path):
                logger.warning(f"检测到不安全的路径: {path}")
                return {"error": "不安全的路径"}
            
            # 执行命令
            result = subprocess.run(
                ["ls", "-la", path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                text=True
            )
            
            # 处理结果
            stdout = result.stdout
            stderr = result.stderr
            
            logger.debug(f"ls命令执行完成: 退出码 = {result.returncode}")
            
            if result.returncode != 0:
                return {
                    "error": stderr,
                    "return_code": result.returncode,
                    "path": path
                }
            
            # 解析输出，格式化为更易读的结构
            lines = stdout.strip().split("\n")
            headers = lines[0] if lines else ""
            
            # 跳过总计行
            file_list = []
            for line in lines[1:]:
                if "total" in line and line.startswith("total"):
                    continue
                file_list.append(line)
            
            return {
                "output": file_list,
                "headers": headers,
                "path": path,
                "count": len(file_list)
            }
        except Exception as e:
            logger.error(f"ls命令执行失败: {str(e)}")
            return {
                "error": f"命令执行失败: {str(e)}",
                "path": path
            }

def is_safe_command(command, allowed_commands):
    """
    检查命令是否安全。
    
    Args:
        command: 要检查的命令
        allowed_commands: 允许的命令列表
        
    Returns:
        命令是否安全
    """
    # 使用shlex分割命令，获取第一个部分（主命令）
    try:
        cmd_parts = shlex.split(command)
        if not cmd_parts:
            return False
        
        main_cmd = cmd_parts[0]
        
        # 检查主命令是否在允许列表中
        return main_cmd in allowed_commands
    except Exception:
        return False

def is_safe_path(path):
    """
    检查路径是否安全。
    
    Args:
        path: 要检查的路径
        
    Returns:
        路径是否安全
    """
    # 禁止使用这些路径模式
    forbidden_patterns = [
        r"^\s*[/]",  # 以/开头（绝对路径）
        r"^\s*~",    # 以~开头（用户主目录）
        r"\.\.",     # 包含..（上级目录）
    ]
    
    # 检查路径是否匹配禁止模式
    for pattern in forbidden_patterns:
        if re.search(pattern, path):
            return False
    
    return True

def teardown():
    """清理插件资源。"""
    logger.info("Bash工具插件已卸载") 