#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 日志配置
LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': PROJECT_ROOT / 'logs' / 'stamp_remover.log',
    'max_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5
}

# 图像处理配置
IMAGE_PROCESSING_CONFIG = {
    'default_threshold': 185,
    'min_threshold': 0,
    'max_threshold': 255,
    'contrast_enhancement': 2.0,
    'sharpness_enhancement': 2.0,
    'supported_formats': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
}

# PDF处理配置
PDF_PROCESSING_CONFIG = {
    'default_dpi': 150,
    'min_dpi': 50,
    'max_dpi': 600,
    'temp_dir_prefix': 'stamp_remover_',
    'max_pages': None,  # None表示处理所有页面
    'max_workers': 4,   # 多线程处理的工作线程数
    'enable_multithreading': True,  # 是否启用多线程处理
    'memory_mode': True  # 是否使用内存模式（不保存临时文件）
}

# 线程配置
THREAD_CONFIG = {
    'max_workers': 4,
    'timeout': 30000,  # 30秒
    'cleanup_timeout': 5000,  # 5秒
    'pdf_processing_workers': 4,  # PDF处理专用线程数
    'image_processing_workers': 2  # 图像处理专用线程数
}

# 颜色配置
COLOR_CONFIG = {
    'red': {'name': '红色', 'channel': 0, 'description': '红色通道'},
    'green': {'name': '绿色', 'channel': 1, 'description': '绿色通道'},
    'blue': {'name': '蓝色', 'channel': 2, 'description': '蓝色通道'},
    'alpha': {'name': '透明', 'channel': 3, 'description': 'Alpha通道'}
}

# UI配置
UI_CONFIG = {
    'window_title': '印章去除工具 v1.0.0',
    'window_size': (1200, 800),
    'min_window_size': (800, 600),
    'theme': 'default'
}

# 临时文件配置
TEMP_CONFIG = {
    'auto_cleanup': True,
    'cleanup_on_exit': True,
    'max_temp_files': 1000
}

