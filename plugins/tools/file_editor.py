#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件编辑工具插件，提供文件的查看、创建和编辑功能。
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from collections import defaultdict

logger = logging.getLogger("file_editor")

# 常量
SNIPPET_LINES = 4
MAX_RESPONSE_LEN = 16000
TRUNCATED_MESSAGE = (
    "<响应已截断><注意>为节省上下文，仅显示文件的一部分。"
    "在查看大文件时，请先使用命令 `grep -n` 查找关键行号，"
    "然后使用视图范围参数查看特定部分。</注意>"
)

def setup(mcp):
    """
    设置文件编辑工具插件。
    
    Args:
        mcp: MCP服务器实例
    """
    logger.info("文件编辑工具插件初始化")
    
    # 文件历史记录，用于撤销操作
    file_history = defaultdict(list)
    
    @mcp.tool()
    async def file_editor(command, path, file_text=None, view_range=None, old_str=None, new_str=None, insert_line=None):
        """
        文件编辑工具，支持查看、创建和编辑文件。
        
        Args:
            command: 命令类型，可选值：'view'、'create'、'str_replace'、'insert'、'undo_edit'
            path: 文件或目录的路径
            file_text: 'create'命令的文件内容
            view_range: 'view'命令的行号范围，如[10, 20]表示查看第10-20行
            old_str: 'str_replace'命令中要替换的字符串
            new_str: 'str_replace'或'insert'命令中的新字符串
            insert_line: 'insert'命令的插入位置行号
            
        Returns:
            操作结果
        """
        logger.debug(f"执行文件操作: {command}, 路径: {path}")
        
        try:
            # 参数验证
            if not command:
                return {"error": "必须指定command参数"}
                
            if not path:
                return {"error": "必须指定path参数"}
                
            # 规范化路径
            path = os.path.abspath(path)
            
            # 执行对应的命令
            if command == "view":
                return await view_file_or_dir(path, view_range)
            elif command == "create":
                return await create_file(path, file_text, file_history)
            elif command == "str_replace":
                return await replace_string(path, old_str, new_str, file_history)
            elif command == "insert":
                return await insert_text(path, insert_line, new_str, file_history)
            elif command == "undo_edit":
                return await undo_edit(path, file_history)
            else:
                return {"error": f"未知命令: {command}。支持的命令: view, create, str_replace, insert, undo_edit"}
        
        except Exception as e:
            logger.error(f"文件操作失败: {str(e)}")
            return {"error": f"文件操作失败: {str(e)}"}

async def view_file_or_dir(path, view_range=None):
    """查看文件或目录内容。"""
    if not os.path.exists(path):
        return {"error": f"路径不存在: {path}"}
        
    if os.path.isdir(path):
        return await view_directory(path)
    else:
        return await view_file(path, view_range)

async def view_directory(path):
    """查看目录内容。"""
    try:
        # 获取目录内的文件和子目录
        dir_contents = []
        for root, dirs, files in os.walk(path, topdown=True, followlinks=False):
            level = root[len(path) + 1:].count(os.sep)
            # 限制只显示2层深度
            if level > 1:
                continue
                
            indent = ' ' * 4 * level
            if root != path:
                # 显示子目录，相对于主目录
                subdir = os.path.relpath(root, path)
                dir_contents.append(f"{indent}📁 {os.path.basename(root)}/")
                
            indent = ' ' * 4 * (level + 1)
            for file in sorted(files):
                # 跳过隐藏文件
                if file.startswith('.'):
                    continue
                dir_contents.append(f"{indent}📄 {file}")
        
        if not dir_contents:
            return {"output": f"目录 {path} 为空或只包含隐藏文件。"}
            
        # 返回目录内容
        return {"output": f"目录 {path} 的内容:\n" + "\n".join(dir_contents)}
        
    except Exception as e:
        logger.error(f"查看目录失败: {str(e)}")
        return {"error": f"查看目录失败: {str(e)}"}

async def view_file(path, view_range=None):
    """查看文件内容。"""
    try:
        if not os.path.isfile(path):
            return {"error": f"路径不是文件: {path}"}
            
        # 读取文件内容
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        # 将内容分行
        lines = content.splitlines()
        total_lines = len(lines)
        
        # 处理查看范围
        if view_range and len(view_range) == 2:
            start_line = max(1, view_range[0])
            end_line = view_range[1] if view_range[1] != -1 else total_lines
            end_line = min(end_line, total_lines)
            
            # 调整为0索引
            start_idx = start_line - 1
            end_idx = end_line
            
            # 提取指定范围的行
            display_lines = lines[start_idx:end_idx]
            
            # 添加行号
            output = [f"{path} (行 {start_line}-{end_line}, 共{total_lines}行):"]
            for i, line in enumerate(display_lines, start_line):
                output.append(f"{i:4d} | {line}")
                
            result = "\n".join(output)
        else:
            # 显示整个文件，带行号
            output = [f"{path} (共{total_lines}行):"]
            
            # 限制过大的文件
            if len(content) > MAX_RESPONSE_LEN:
                # 只显示开头部分
                preview_lines = min(total_lines, 200)
                for i, line in enumerate(lines[:preview_lines], 1):
                    output.append(f"{i:4d} | {line}")
                    
                output.append(TRUNCATED_MESSAGE)
            else:
                for i, line in enumerate(lines, 1):
                    output.append(f"{i:4d} | {line}")
                    
            result = "\n".join(output)
            
        return {"output": result}
        
    except Exception as e:
        logger.error(f"查看文件失败: {str(e)}")
        return {"error": f"查看文件失败: {str(e)}"}

async def create_file(path, file_text, file_history):
    """创建新文件。"""
    try:
        if os.path.exists(path):
            return {"error": f"文件已存在: {path}，不能使用create命令覆盖现有文件"}
            
        # 确保目录存在
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        # 写入文件内容
        with open(path, 'w', encoding='utf-8') as f:
            f.write(file_text or "")
            
        # 保存到历史记录
        file_history[path].append(file_text or "")
        
        return {"output": f"文件创建成功: {path}"}
        
    except Exception as e:
        logger.error(f"创建文件失败: {str(e)}")
        return {"error": f"创建文件失败: {str(e)}"}

async def replace_string(path, old_str, new_str, file_history):
    """在文件中替换字符串。"""
    try:
        if not os.path.isfile(path):
            return {"error": f"路径不是文件: {path}"}
            
        if not old_str:
            return {"error": "必须指定old_str参数"}
            
        # 读取当前文件内容
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        # 检查old_str是否存在且唯一
        if old_str not in content:
            return {"error": f"未找到要替换的字符串。请确保old_str与文件中的内容完全匹配，包括空格和换行符。"}
            
        # 检查是否唯一
        if content.count(old_str) > 1:
            return {"error": f"找到多个匹配的字符串。请提供更具体的上下文，确保old_str在文件中是唯一的。"}
            
        # 保存到历史记录
        file_history[path].append(content)
        
        # 替换字符串
        new_content = content.replace(old_str, new_str or "")
        
        # 写入文件
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return {"output": f"字符串替换成功，文件已更新: {path}"}
        
    except Exception as e:
        logger.error(f"替换字符串失败: {str(e)}")
        return {"error": f"替换字符串失败: {str(e)}"}

async def insert_text(path, insert_line, new_str, file_history):
    """在指定行插入文本。"""
    try:
        if not os.path.isfile(path):
            return {"error": f"路径不是文件: {path}"}
            
        if insert_line is None:
            return {"error": "必须指定insert_line参数"}
            
        if new_str is None:
            return {"error": "必须指定new_str参数"}
            
        # 读取当前文件内容
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            
        # 检查行号是否有效
        if insert_line < 1 or insert_line > len(lines) + 1:
            return {"error": f"无效的行号: {insert_line}。文件共有{len(lines)}行。"}
            
        # 保存到历史记录
        file_history[path].append("".join(lines))
        
        # 确保new_str以换行符结尾
        if not new_str.endswith('\n'):
            new_str += '\n'
            
        # 插入文本
        lines.insert(insert_line - 1, new_str)
        
        # 写入文件
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            
        return {"output": f"文本已插入到第{insert_line}行，文件已更新: {path}"}
        
    except Exception as e:
        logger.error(f"插入文本失败: {str(e)}")
        return {"error": f"插入文本失败: {str(e)}"}

async def undo_edit(path, file_history):
    """撤销上一次编辑。"""
    try:
        if not os.path.isfile(path):
            return {"error": f"路径不是文件: {path}"}
            
        # 检查历史记录
        if path not in file_history or not file_history[path]:
            return {"error": f"没有可撤销的编辑历史记录: {path}"}
            
        # 获取上一个版本
        previous_content = file_history[path].pop()
        
        # 写入文件
        with open(path, 'w', encoding='utf-8') as f:
            f.write(previous_content)
            
        return {"output": f"成功撤销上次编辑，文件已恢复: {path}"}
        
    except Exception as e:
        logger.error(f"撤销编辑失败: {str(e)}")
        return {"error": f"撤销编辑失败: {str(e)}"}

def teardown():
    """清理插件资源。"""
    logger.info("文件编辑工具插件已卸载") 