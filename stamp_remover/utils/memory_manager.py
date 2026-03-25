#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内存管理模块
"""

import gc
import os
import sys
from typing import Optional, Tuple
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


def get_memory_usage() -> Tuple[float, float]:
    """获取当前进程的内存使用情况
    
    Returns:
        (已使用内存MB, 可用内存MB)
    """
    try:
        import psutil
        process = psutil.Process(os.getpid())
        used_mb = process.memory_info().rss / (1024 * 1024)
        
        system_memory = psutil.virtual_memory()
        available_mb = system_memory.available / (1024 * 1024)
        
        return used_mb, available_mb
    except ImportError:
        logger.debug("psutil未安装，无法获取精确内存使用情况")
        return 0.0, 0.0
    except Exception as e:
        logger.debug(f"获取内存使用情况失败: {e}")
        return 0.0, 0.0


def check_memory_available(required_mb: float, threshold_mb: float = 100.0) -> Tuple[bool, float]:
    """检查是否有足够的可用内存
    
    Args:
        required_mb: 需要的内存量（MB）
        threshold_mb: 最小保留内存阈值（MB）
    
    Returns:
        (是否有足够内存, 可用内存MB)
    """
    _, available_mb = get_memory_usage()
    
    if available_mb <= 0:
        return True, 0.0
    
    return available_mb >= (required_mb + threshold_mb), available_mb


def force_garbage_collection():
    """强制执行垃圾回收"""
    collected = gc.collect()
    logger.debug(f"垃圾回收完成，回收了 {collected} 个对象")
    return collected


def estimate_image_memory_size(width: int, height: int, channels: int = 3) -> float:
    """估算图像在内存中的大小
    
    Args:
        width: 图像宽度
        height: 图像高度
        channels: 通道数
    
    Returns:
        估算的内存大小（MB）
    """
    bytes_per_pixel = channels
    total_bytes = width * height * bytes_per_pixel
    overhead_factor = 1.5
    return (total_bytes * overhead_factor) / (1024 * 1024)


def estimate_pdf_page_memory_size(width: int, height: int, dpi: int = 150) -> float:
    """估算PDF页面转换为图片后的内存大小
    
    Args:
        width: 页面宽度（点）
        height: 页面高度（点）
        dpi: 渲染DPI
    
    Returns:
        估算的内存大小（MB）
    """
    scale = dpi / 72.0
    pixel_width = int(width * scale)
    pixel_height = int(height * scale)
    
    return estimate_image_memory_size(pixel_width, pixel_height, 4)


class MemoryManager:
    """内存管理器"""
    
    def __init__(self, max_memory_mb: float = 500.0, warning_threshold: float = 0.8):
        self.max_memory_mb = max_memory_mb
        self.warning_threshold = warning_threshold
        self._current_usage = 0.0
    
    def allocate(self, size_mb: float) -> bool:
        """尝试分配内存
        
        Args:
            size_mb: 需要分配的内存大小（MB）
        
        Returns:
            是否成功分配
        """
        if self._current_usage + size_mb > self.max_memory_mb:
            logger.warning(f"内存分配失败: 需要 {size_mb:.1f}MB，已使用 {self._current_usage:.1f}MB，上限 {self.max_memory_mb:.1f}MB")
            return False
        
        self._current_usage += size_mb
        logger.debug(f"分配内存: {size_mb:.1f}MB，当前使用: {self._current_usage:.1f}MB")
        return True
    
    def release(self, size_mb: float):
        """释放内存
        
        Args:
            size_mb: 需要释放的内存大小（MB）
        """
        self._current_usage = max(0, self._current_usage - size_mb)
        logger.debug(f"释放内存: {size_mb:.1f}MB，当前使用: {self._current_usage:.1f}MB")
    
    def get_usage_percentage(self) -> float:
        """获取内存使用百分比"""
        if self.max_memory_mb <= 0:
            return 0.0
        return self._current_usage / self.max_memory_mb
    
    def is_warning_level(self) -> bool:
        """检查是否达到警告级别"""
        return self.get_usage_percentage() >= self.warning_threshold
    
    def can_allocate(self, size_mb: float) -> bool:
        """检查是否可以分配指定大小的内存"""
        return self._current_usage + size_mb <= self.max_memory_mb
    
    def reset(self):
        """重置内存使用统计"""
        self._current_usage = 0.0
        force_garbage_collection()
    
    def get_status(self) -> dict:
        """获取内存状态"""
        return {
            'current_usage_mb': self._current_usage,
            'max_memory_mb': self.max_memory_mb,
            'usage_percentage': self.get_usage_percentage(),
            'is_warning': self.is_warning_level(),
            'available_mb': self.max_memory_mb - self._current_usage
        }
