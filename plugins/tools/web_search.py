#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Web搜索工具插件，提供网络搜索功能。
"""

import asyncio
import logging
import json
import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger("web_search")

# 定义搜索引擎URL模板
SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q={query}&num={num_results}&hl={lang}",
    "bing": "https://www.bing.com/search?q={query}&count={num_results}&setlang={lang}",
    "baidu": "https://www.baidu.com/s?wd={query}&rn={num_results}",
    "duckduckgo": "https://html.duckduckgo.com/html/?q={query}"
}

# 默认请求头
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

def setup(mcp):
    """
    设置Web搜索工具插件。
    
    Args:
        mcp: MCP服务器实例
    """
    logger.info("Web搜索工具插件初始化")
    
    # 获取配置信息
    config = mcp.get_config().get("tool_configs", {}).get("web_search", {})
    default_engine = config.get("default_engine", "google")
    default_num_results = config.get("max_results", 5)
    default_timeout = config.get("timeout", 15)
    
    @mcp.tool()
    async def web_search(
        query: str, 
        num_results: int = default_num_results, 
        engine: str = default_engine, 
        lang: str = "en", 
        fetch_content: bool = False
    ) -> Dict[str, Any]:
        """
        执行网络搜索并返回结果。
        
        Args:
            query: 搜索查询字符串
            num_results: 返回的最大结果数量，默认为配置中设置的值
            engine: 搜索引擎，支持 "google", "bing", "baidu", "duckduckgo"
            lang: 搜索结果的语言代码
            fetch_content: 是否获取搜索结果页面的内容
            
        Returns:
            包含搜索结果的字典，包括标题、URL和摘要
            
        Raises:
            ValueError: 当搜索引擎不受支持或其他参数无效时
        """
        logger.info(f"执行Web搜索: query='{query}', engine='{engine}', num_results={num_results}")
        
        # 验证参数
        if not query or not isinstance(query, str):
            raise ValueError("搜索查询不能为空且必须是字符串")
        
        if not isinstance(num_results, int) or num_results <= 0:
            raise ValueError("结果数量必须是正整数")
        
        if engine not in SEARCH_ENGINES:
            supported_engines = ", ".join(SEARCH_ENGINES.keys())
            raise ValueError(f"不支持的搜索引擎: {engine}。支持的引擎: {supported_engines}")
        
        # 构建搜索URL
        search_url = SEARCH_ENGINES[engine].format(
            query=requests.utils.quote(query),
            num_results=min(num_results, 20),  # 限制最大结果数
            lang=lang
        )
        
        try:
            # 发送HTTP请求
            response = requests.get(
                search_url, 
                headers=DEFAULT_HEADERS, 
                timeout=default_timeout
            )
            response.raise_for_status()
            
            # 解析搜索结果
            search_results = await _parse_search_results(
                response.text, 
                engine, 
                num_results
            )
            
            # 如果需要，获取页面内容
            if fetch_content and search_results:
                for i, result in enumerate(search_results[:3]):  # 限制只获取前3个结果的内容
                    if "url" in result:
                        try:
                            content = await _fetch_page_content(result["url"], default_timeout)
                            search_results[i]["content"] = content[:2000]  # 限制内容长度
                        except Exception as e:
                            logger.warning(f"获取页面内容失败: {result['url']}, 错误: {str(e)}")
                            search_results[i]["content_error"] = str(e)
            
            # 格式化结果
            formatted_results = _format_search_results(search_results, query)
            
            return {
                "query": query,
                "engine": engine,
                "results_count": len(search_results),
                "results": search_results,
                "formatted_text": formatted_results
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"搜索请求失败: {str(e)}")
            return {
                "error": f"搜索请求失败: {str(e)}",
                "query": query,
                "engine": engine
            }
        except Exception as e:
            logger.error(f"搜索过程中出错: {str(e)}")
            return {
                "error": f"搜索过程中出错: {str(e)}",
                "query": query,
                "engine": engine
            }
    
    async def _parse_search_results(html_content, engine, max_results):
        """
        解析搜索引擎返回的HTML内容，提取搜索结果。
        
        Args:
            html_content: HTML内容
            engine: 搜索引擎名称
            max_results: 最大结果数量
            
        Returns:
            解析后的搜索结果列表
        """
        results = []
        soup = BeautifulSoup(html_content, "html.parser")
        
        if engine == "google":
            # 解析Google搜索结果
            for div in soup.select("div.g"):
                try:
                    title_element = div.select_one("h3")
                    if not title_element:
                        continue
                    
                    title = title_element.get_text()
                    link = div.select_one("a")
                    url = link["href"] if link and "href" in link.attrs else ""
                    
                    # 获取摘要
                    snippet_element = div.select_one("div.VwiC3b")
                    snippet = snippet_element.get_text() if snippet_element else ""
                    
                    # 只添加有效结果
                    if title and url and url.startswith("http"):
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet
                        })
                        
                        if len(results) >= max_results:
                            break
                except Exception as e:
                    logger.warning(f"解析Google结果时出错: {str(e)}")
        
        elif engine == "bing":
            # 解析Bing搜索结果
            for li in soup.select("li.b_algo"):
                try:
                    title_element = li.select_one("h2 a")
                    if not title_element:
                        continue
                    
                    title = title_element.get_text()
                    url = title_element["href"] if "href" in title_element.attrs else ""
                    
                    # 获取摘要
                    snippet_element = li.select_one("p")
                    snippet = snippet_element.get_text() if snippet_element else ""
                    
                    # 只添加有效结果
                    if title and url and url.startswith("http"):
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet
                        })
                        
                        if len(results) >= max_results:
                            break
                except Exception as e:
                    logger.warning(f"解析Bing结果时出错: {str(e)}")
        
        # 添加其他搜索引擎的解析逻辑...
        
        # 如果没有找到结果，返回一个解析错误信息
        if not results:
            logger.warning(f"无法从{engine}解析搜索结果")
            results.append({
                "title": "无法解析搜索结果",
                "url": "",
                "snippet": f"无法从{engine}解析搜索结果，可能是解析器需要更新或搜索引擎改变了页面结构。"
            })
        
        return results
    
    async def _fetch_page_content(url, timeout):
        """
        获取页面内容。
        
        Args:
            url: 页面URL
            timeout: 请求超时时间（秒）
            
        Returns:
            页面的纯文本内容
        """
        try:
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 移除脚本、样式和其他不需要的元素
            for element in soup(["script", "style", "meta", "noscript", "iframe"]):
                element.extract()
            
            # 获取纯文本
            text = soup.get_text()
            
            # 清理文本（移除多余空白）
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
        except Exception as e:
            logger.error(f"获取页面内容失败 {url}: {str(e)}")
            raise ValueError(f"获取页面内容失败: {str(e)}")
    
    def _format_search_results(results, query):
        """
        将搜索结果格式化为可读文本。
        
        Args:
            results: 搜索结果列表
            query: 搜索查询
            
        Returns:
            格式化的文本
        """
        if not results:
            return f"未找到关于\"{query}\"的结果。"
        
        formatted_text = f"关于\"{query}\"的搜索结果：\n\n"
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "无标题")
            url = result.get("url", "")
            snippet = result.get("snippet", "无摘要")
            
            formatted_text += f"{i}. {title}\n"
            formatted_text += f"   URL: {url}\n"
            formatted_text += f"   摘要: {snippet}\n\n"
        
        return formatted_text

def teardown():
    """清理插件资源。"""
    logger.info("Web搜索工具插件已卸载") 