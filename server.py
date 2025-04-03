#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCP即插即用服务器主入口文件。
"""

import argparse
import logging
import os
import sys

# 确保当前目录在Python路径中
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.server import create_server


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数。

    Returns:
        解析后的参数
    """
    parser = argparse.ArgumentParser(description="MCP即插即用服务器")
    parser.add_argument(
        "--name",
        type=str,
        help="服务器名称（默认从配置读取）",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.json",
        help="配置文件路径（默认: config/config.json）",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        help="传输方式：stdio或http（默认从配置读取）",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式",
    )
    return parser.parse_args()


def main() -> None:
    """主函数，启动MCP服务器。"""
    args = parse_args()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 创建服务器实例
    server = create_server(args.name, args.config)
    
    # 运行服务器
    server.run(args.transport)


if __name__ == "__main__":
    main() 