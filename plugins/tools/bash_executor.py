#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bash命令执行工具插件，提供安全的Shell命令执行功能。
"""

import asyncio
import logging
import os
import re
import signal
import subprocess
from typing import Dict, Optional, List

logger = logging.getLogger("bash_executor")

# Bash会话状态，全局变量在插件内共享
_bash_process: Optional[asyncio.subprocess.Process] = None
_started: bool = False
_output_delay: float = 0.2  # seconds
_timeout: float = 30.0  # seconds
_sentinel: str = "<<exit>>"

def setup(mcp):
    """
    设置Bash命令执行工具插件。
    
    Args:
        mcp: MCP服务器实例
    """
    # 获取插件配置
    config = mcp.config.get("tool_configs", {}).get("bash", {})
    allowed_commands = config.get("allowed_commands", ["ls", "cat", "echo", "grep", "find"])
    enabled = config.get("enabled", True)
    
    logger.info(f"Bash命令执行工具插件初始化: 已启用 = {enabled}, 允许的命令 = {allowed_commands}")
    
    if not enabled:
        logger.info("Bash命令执行工具插件已禁用")
        return
    
    @mcp.tool()
    async def bash(command, restart=False):
        """
        执行Bash命令。
        
        Args:
            command: 要执行的bash命令，可以是空字符串以查看前一个命令的更多输出，可以是'ctrl+c'以中断当前运行的进程
            restart: 是否重启bash会话（如果会话出错，可以尝试重启）
            
        Returns:
            命令执行结果
        """
        global _bash_process, _started
        
        logger.debug(f"执行Bash命令: {command}, restart={restart}")
        
        try:
            # 如果请求重启或会话尚未启动
            if restart or not _started:
                if _bash_process and _bash_process.returncode is None:
                    # 尝试终止当前进程
                    try:
                        _bash_process.terminate()
                        await asyncio.sleep(0.5)
                    except Exception:
                        pass
                
                # 启动新会话
                await _start_bash_session()
                return {"system": "bash会话已重启"}
            
            # 检查会话状态
            if not _started or _bash_process is None:
                return {"error": "bash会话未启动，请使用restart=True参数重启"}
            
            if _bash_process.returncode is not None:
                return {"error": f"bash已退出，返回码 {_bash_process.returncode}，请使用restart=True参数重启"}
            
            # 处理特殊命令
            if command == "ctrl+c":
                # 发送中断信号
                try:
                    if _bash_process.returncode is None:
                        os.killpg(os.getpgid(_bash_process.pid), signal.SIGINT)
                        return {"system": "已发送中断信号"}
                except Exception as e:
                    return {"error": f"发送中断信号失败: {str(e)}"}
            
            # 检查命令安全性
            if command and not _is_safe_command(command, allowed_commands):
                return {
                    "error": f"不安全的命令: {command}\n仅支持以下命令: {', '.join(allowed_commands)}",
                    "allowed_commands": allowed_commands
                }
            
            # 执行命令
            result = await _run_bash_command(command)
            return result
            
        except Exception as e:
            logger.error(f"命令执行错误: {str(e)}")
            return {"error": f"命令执行错误: {str(e)}"}

async def _start_bash_session():
    """启动一个新的Bash会话。"""
    global _bash_process, _started
    
    if _started and _bash_process and _bash_process.returncode is None:
        logger.debug("会话已经启动")
        return
    
    logger.debug("启动新的bash会话")
    
    try:
        # 使用subprocess创建子进程
        _bash_process = await asyncio.create_subprocess_shell(
            "/bin/bash",
            preexec_fn=os.setsid,  # 使用新的进程组，以便可以终止整个组
            shell=True,
            bufsize=0,  # 不缓冲
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        _started = True
        logger.info("bash会话已启动")
        
    except Exception as e:
        _started = False
        logger.error(f"启动bash会话失败: {str(e)}")
        raise

async def _run_bash_command(command):
    """在Bash会话中执行命令。"""
    global _bash_process, _started
    
    if not _started or not _bash_process or _bash_process.returncode is not None:
        return {"error": "bash会话未启动或已退出"}
    
    # 确保stdin, stdout, stderr存在
    if not _bash_process.stdin or not _bash_process.stdout or not _bash_process.stderr:
        return {"error": "bash会话I/O流未初始化"}
    
    try:
        # 发送命令并添加sentinel以便判断命令执行完毕
        _bash_process.stdin.write(f"{command}; echo '{_sentinel}'\n".encode())
        await _bash_process.stdin.drain()
        
        # 读取命令输出
        output = ""
        error = ""
        
        try:
            async with asyncio.timeout(_timeout):
                while True:
                    # 等待一小段时间，让输出积累
                    await asyncio.sleep(_output_delay)
                    
                    # 读取当前缓冲区内容
                    stdout_buffer = _bash_process.stdout._buffer.decode()
                    stderr_buffer = _bash_process.stderr._buffer.decode()
                    
                    if _sentinel in stdout_buffer:
                        # 找到sentinel，表示命令执行完毕
                        output = stdout_buffer[:stdout_buffer.index(_sentinel)]
                        error = stderr_buffer
                        
                        # 清除缓冲区
                        _bash_process.stdout._buffer.clear()
                        _bash_process.stderr._buffer.clear()
                        break
        except asyncio.TimeoutError:
            return {
                "error": f"命令执行超时（{_timeout}秒）。发送SIGINT结束进程",
                "output": stdout_buffer if 'stdout_buffer' in locals() else "",
                "partial": True
            }
        
        # 清理输出末尾的换行符
        if output.endswith("\n"):
            output = output[:-1]
        
        if error.endswith("\n"):
            error = error[:-1]
        
        result = {"output": output}
        
        if error:
            result["error"] = error
            
        return result
        
    except Exception as e:
        logger.error(f"执行命令失败: {str(e)}")
        return {"error": f"执行命令失败: {str(e)}"}

def _is_safe_command(command, allowed_commands):
    """
    检查命令是否安全。
    
    Args:
        command: 要检查的命令
        allowed_commands: 允许的命令列表
        
    Returns:
        命令是否安全
    """
    # 空命令是安全的（用于获取前一命令的更多输出）
    if not command.strip():
        return True
    
    # 提取主命令
    # 使用正则表达式匹配命令中的第一个单词（管道和多命令前）
    pattern = r'^(sudo\s+)?([a-zA-Z0-9_\-]+)'
    match = re.match(pattern, command.strip())
    
    if not match:
        return False
    
    main_cmd = match.group(2)
    
    # 检查主命令是否在允许列表中
    return main_cmd in allowed_commands

def teardown():
    """清理插件资源。"""
    global _bash_process, _started
    
    logger.info("清理Bash命令执行工具插件资源")
    
    # 尝试终止bash进程
    if _started and _bash_process and _bash_process.returncode is None:
        try:
            _bash_process.terminate()
            logger.debug("bash进程已终止")
        except Exception as e:
            logger.error(f"终止bash进程失败: {str(e)}")
    
    _started = False
    _bash_process = None
    
    logger.info("Bash命令执行工具插件已卸载") 