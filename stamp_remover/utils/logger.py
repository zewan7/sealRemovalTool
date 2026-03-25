#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志配置模块
解决日志配置重复导致重复记录的问题
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional

# 全局标志，用于确保日志只配置一次
_logging_configured = False


def setup_logging(
    level: int = logging.INFO,
    log_dir: Optional[Path] = None,
    log_file: str = "stamp_remover.log",
    console_output: bool = True,
    file_output: bool = True,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    设置统一的日志配置
    
    使用全局标志确保日志只配置一次，避免重复记录
    
    Args:
        level: 日志级别，默认为 INFO
        log_dir: 日志目录，默认为项目根目录下的 logs 文件夹
        log_file: 日志文件名
        console_output: 是否输出到控制台
        file_output: 是否输出到文件
        format_string: 自定义日志格式
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    global _logging_configured
    
    # 如果日志已经配置过，直接返回根记录器
    if _logging_configured:
        return logging.getLogger("stamp_remover")
    
    # 设置日志格式
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(format_string)
    
    # 获取根记录器
    root_logger = logging.getLogger("stamp_remover")
    root_logger.setLevel(level)
    
    # 清除现有的处理器（如果有）
    root_logger.handlers.clear()
    
    handlers = []
    
    # 文件处理器
    if file_output:
        if log_dir is None:
            # 默认日志目录
            project_root = Path(__file__).parent.parent.parent
            log_dir = project_root / "logs"
        
        log_dir.mkdir(exist_ok=True)
        log_path = log_dir / log_file
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    # 添加处理器到根记录器
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # 设置标志，表示日志已配置
    _logging_configured = True
    
    root_logger.info("日志系统已初始化")
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    
    确保在使用前已经调用过 setup_logging()
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 日志记录器
    """
    global _logging_configured
    
    # 如果日志未配置，自动配置
    if not _logging_configured:
        setup_logging()
    
    # 返回以 stamp_remover 为前缀的记录器
    if not name.startswith("stamp_remover"):
        name = f"stamp_remover.{name}"
    
    return logging.getLogger(name)


def reset_logging():
    """
    重置日志配置（主要用于测试）
    """
    global _logging_configured
    _logging_configured = False
    
    # 清除所有处理器
    root_logger = logging.getLogger("stamp_remover")
    root_logger.handlers.clear()
