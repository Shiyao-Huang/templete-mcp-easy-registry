#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
计算器工具插件，提供数学计算功能。
"""

import logging
import math
import re

logger = logging.getLogger("calculator_tool")

def setup(mcp):
    """
    设置计算器工具插件。
    
    Args:
        mcp: MCP服务器实例
    """
    logger.info("计算器工具插件初始化")
    
    @mcp.tool()
    def calculator(expression):
        """
        执行数学计算。
        
        Args:
            expression: 数学表达式
            
        Returns:
            计算结果或错误消息
        """
        logger.debug(f"执行计算: {expression}")
        
        try:
            # 检查表达式安全性
            if not is_safe_expression(expression):
                logger.warning(f"检测到不安全的表达式: {expression}")
                return {"error": "不安全的表达式，仅支持基本数学运算"}
            
            # 创建安全的计算环境
            safe_env = {
                'abs': abs,
                'max': max,
                'min': min,
                'sum': sum,
                'round': round,
                'pow': pow,
                'int': int,
                'float': float,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'sqrt': math.sqrt,
                'pi': math.pi,
                'e': math.e
            }
            
            # 执行计算
            result = eval(expression, {"__builtins__": {}}, safe_env)
            
            logger.debug(f"计算结果: {result}")
            return {
                "result": result,
                "expression": expression
            }
        except Exception as e:
            logger.error(f"计算失败: {str(e)}")
            return {
                "error": f"计算错误: {str(e)}",
                "expression": expression
            }
    
    @mcp.tool()
    def solve_equation(equation, variable="x"):
        """
        求解简单方程。
        
        Args:
            equation: 方程式（形如 "x + 5 = 10"）
            variable: 要求解的变量，默认为 "x"
            
        Returns:
            求解结果或错误消息
        """
        logger.debug(f"求解方程: {equation}, 变量: {variable}")
        
        try:
            # 检查方程式格式
            if "=" not in equation:
                return {"error": f"无效的方程式，缺少等号: {equation}"}
            
            # 分离等号两边
            left, right = equation.split("=", 1)
            left = left.strip()
            right = right.strip()
            
            # 转换为 "左侧 - 右侧 = 0" 形式
            normalized = f"({left}) - ({right})"
            
            # 简单线性方程求解（这只是一个演示，不能处理所有情况）
            # 思路：将所有含变量的项集中到左侧，常数项到右侧
            terms = re.split(r'([+-])', normalized)
            if not terms[0]:  # 如果第一项是空的（表达式以+或-开头）
                terms = terms[1:]
                
            left_terms = []
            right_value = 0
            
            i = 0
            while i < len(terms):
                term = terms[i].strip()
                sign = "+" if i == 0 else terms[i-1]
                
                if not term:
                    i += 1
                    continue
                    
                if variable in term:
                    # 变量项移到左侧
                    coefficient = 1
                    if term.replace(variable, ""):
                        coefficient = float(term.replace(variable, "")) if term.replace(variable, "") != "" else 1
                    if sign == "-":
                        coefficient = -coefficient
                    left_terms.append(coefficient)
                else:
                    # 常数项移到右侧
                    try:
                        value = float(term)
                        if sign == "-":
                            value = -value
                        right_value -= value  # 注意这里是减去，因为我们把所有项移到左侧
                    except ValueError:
                        return {"error": f"无法解析项: {term}"}
                
                i += 2  # 跳过下一个符号
                
            # 计算左侧系数之和
            left_coefficient = sum(left_terms)
            
            if left_coefficient == 0:
                if right_value == 0:
                    return {"result": "无穷多解", "equation": equation}
                else:
                    return {"result": "无解", "equation": equation}
            
            # 求解变量值
            solution = right_value / left_coefficient
            
            logger.debug(f"方程求解结果: {variable} = {solution}")
            return {
                "result": solution,
                "variable": variable,
                "equation": equation
            }
        except Exception as e:
            logger.error(f"求解方程失败: {str(e)}")
            return {
                "error": f"求解错误: {str(e)}",
                "equation": equation
            }

def is_safe_expression(expr):
    """
    检查表达式是否安全（不包含潜在的危险操作）。
    
    Args:
        expr: 要检查的表达式
        
    Returns:
        表达式是否安全
    """
    # 禁止使用这些关键字和符号
    forbidden = [
        "import", "exec", "eval", "compile", "globals", "locals", "getattr", "setattr",
        "delattr", "__", "open", "file", "os.", "sys.", "subprocess", "lambda"
    ]
    
    # 检查是否存在禁止的关键字
    for keyword in forbidden:
        if keyword in expr:
            return False
    
    # 只允许包含数字、运算符、空格和一些基本函数
    allowed_pattern = r'^[0-9\s\+\-\*\/\(\)\.\,\<\>\=\!\&\|abs\max\min\sum\round\pow\int\float\sin\cos\tan\sqrt\pi\e]+$'
    return bool(re.match(allowed_pattern, expr))

def teardown():
    """清理插件资源。"""
    logger.info("计算器工具插件已卸载")