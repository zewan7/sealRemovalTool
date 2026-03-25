#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置模块
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import threading

_logger_lock = threading.Lock()
_logger_configured = False


def setup_logging(log_level: int = logging.INFO, 
                  log_file: Optional[str] = None,
                  force_reconfigure: bool = False) -> logging.Logger:
    """设置日志配置（单例模式，防止重复配置）
    
    Args:
        log_level: 日志级别
        log_file: 日志文件路径，如果为None则使用默认路径
        force_reconfigure: 是否强制重新配置
    
    Returns:
        根日志器
    """
    global _logger_configured
    
    with _logger_lock:
        if _logger_configured and not force_reconfigure:
            return logging.getLogger()
        
        root_logger = logging.getLogger()
        
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        root_logger.setLevel(log_level)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        if log_file is None:
            project_root = Path(__file__).parent.parent
            logs_dir = project_root / "logs"
            logs_dir.mkdir(exist_ok=True)
            log_file = str(logs_dir / "stamp_remover.log")
        
        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.warning(f"无法创建日志文件: {e}")
        
        _logger_configured = True
        
        return root_logger


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志器
    
    Args:
        name: 日志器名称
    
    Returns:
        日志器实例
    """
    if not _logger_configured:
        setup_logging()
    
    return logging.getLogger(name)


def reset_logging():
    """重置日志配置（主要用于测试）"""
    global _logger_configured
    
    with _logger_lock:
        root_logger = logging.getLogger()
        
        for handler in root_logger.handlers[:]:
            try:
                handler.close()
            except Exception:
                pass
            root_logger.removeHandler(handler)
        
        _logger_configured = False
